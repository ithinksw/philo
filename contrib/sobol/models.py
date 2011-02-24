from django.conf.urls.defaults import patterns, url
from django.contrib import messages
from django.db import models
from django.http import HttpResponseRedirect, Http404
from django.utils import simplejson as json
from philo.contrib.sobol import registry
from philo.contrib.sobol.forms import SearchForm
from philo.contrib.sobol.utils import HASH_REDIRECT_GET_KEY, URL_REDIRECT_GET_KEY, SEARCH_ARG_GET_KEY, check_redirect_hash
from philo.exceptions import ViewCanNotProvideSubpath
from philo.models import MultiView, Page
from philo.models.fields import SlugMultipleChoiceField
from philo.validators import RedirectValidator
import datetime
try:
	import eventlet
except:
	eventlet = False


class Search(models.Model):
	string = models.TextField()
	
	def __unicode__(self):
		return self.string
	
	def get_favored_results(self, error=5):
		"""Calculate the set of most-favored results. A higher error
		will cause this method to be more reticent about adding new
		items."""
		results = self.result_urls.values_list('pk', 'url',)
		
		result_dict = {}
		for pk, url in results:
			result_dict[pk] = {'url': url, 'value': 0}
		
		clicks = Click.objects.filter(result__pk__in=result_dict.keys()).values_list('result__pk', 'datetime')
		
		now = datetime.datetime.now()
		
		def datetime_value(dt):
			days = (now - dt).days
			if days < 0:
				raise ValueError("Click dates must be in the past.")
			if days == 0:
				value = 1.0
			else:
				value = 1.0/days**2
			return value
		
		for pk, dt in clicks:
			value = datetime_value(dt)
			result_dict[pk]['value'] += value
		
		#TODO: is there a reasonable minimum value for consideration?
		subsets = {}
		for d in result_dict.values():
			subsets.setdefault(d['value'], []).append(d)
		
		# Now calculate the result set.
		results = []
		
		def cost(value):
			return error*sum([(value - item['value'])**2 for item in results])
		
		for value, subset in sorted(subsets.items(), cmp=lambda x,y: cmp(y[0], x[0])):
			if value > cost(value):
				results += subset
			else:
				break
		return results
	
	class Meta:
		ordering = ['string']
		verbose_name_plural = 'searches'


class ResultURL(models.Model):
	search = models.ForeignKey(Search, related_name='result_urls')
	url = models.TextField(validators=[RedirectValidator()])
	
	def __unicode__(self):
		return self.url
	
	class Meta:
		ordering = ['url']


class Click(models.Model):
	result = models.ForeignKey(ResultURL, related_name='clicks')
	datetime = models.DateTimeField()
	
	def __unicode__(self):
		return self.datetime.strftime('%B %d, %Y %H:%M:%S')
	
	class Meta:
		ordering = ['datetime']
		get_latest_by = 'datetime'


class SearchView(MultiView):
	results_page = models.ForeignKey(Page, related_name='search_results_related')
	searches = SlugMultipleChoiceField(choices=registry.iterchoices())
	enable_ajax_api = models.BooleanField("Enable AJAX API", default=True)
	placeholder_text = models.CharField(max_length=75, default="Search")
	
	def __unicode__(self):
		return u"%s (%s)" % (self.placeholder_text, u", ".join([display for slug, display in registry.iterchoices()]))
	
	def get_reverse_params(self, obj):
		raise ViewCanNotProvideSubpath
	
	@property
	def urlpatterns(self):
		urlpatterns = patterns('',
			url(r'^$', self.results_view, name='results'),
		)
		if self.enable_ajax_api:
			urlpatterns += patterns('',
				url(r'^(?P<slug>[\w-]+)', self.ajax_api_view, name='ajax_api_view')
			)
		return urlpatterns
	
	def get_search_instance(self, slug, search_string):
		return registry[slug](search_string.lower())
	
	def results_view(self, request, extra_context=None):
		results = None
		
		context = self.get_context()
		context.update(extra_context or {})
		
		if SEARCH_ARG_GET_KEY in request.GET:
			form = SearchForm(request.GET)
			
			if form.is_valid():
				search_string = request.GET[SEARCH_ARG_GET_KEY].lower()
				url = request.GET.get(URL_REDIRECT_GET_KEY)
				hash = request.GET.get(HASH_REDIRECT_GET_KEY)
				
				if url and hash:
					if check_redirect_hash(hash, search_string, url):
						# Create the necessary models
						search = Search.objects.get_or_create(string=search_string)[0]
						result_url = search.result_urls.get_or_create(url=url)[0]
						result_url.clicks.create(datetime=datetime.datetime.now())
						return HttpResponseRedirect(url)
					else:
						messages.add_message(request, messages.INFO, "The link you followed had been tampered with. Here are all the results for your search term instead!")
						# TODO: Should search_string be escaped here?
						return HttpResponseRedirect("%s?%s=%s" % (request.path, SEARCH_ARG_GET_KEY, search_string))
				if not self.enable_ajax_api:
					search_instances = []
					if eventlet:
						pool = eventlet.GreenPool()
					for slug in self.searches:
						search_instance = self.get_search_instance(slug, search_string)
						search_instances.append(search_instance)
						if eventlet:
							pool.spawn_n(self.make_result_cache, search_instance)
						else:
							self.make_result_cache(search_instance)
					if eventlet:
						pool.waitall()
					context.update({
						'searches': search_instances
					})
		else:
			form = SearchForm()
		
		context.update({
			'form': form
		})
		return self.results_page.render_to_response(request, extra_context=context)
	
	def make_result_cache(self, search_instance):
		search_instance.results
	
	def ajax_api_view(self, request, slug, extra_context=None):
		search_string = request.GET.get(SEARCH_ARG_GET_KEY)
		
		if not request.is_ajax() or not self.enable_ajax_api or slug not in self.searches or search_string is None:
			raise Http404
		
		search_instance = self.get_search_instance(slug, search_string)
		response = json.dumps({
			'results': search_instance.results,
			'template': search_instance.get_template()
		})
		return response