from django.conf.urls.defaults import patterns, url
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import models
from django.http import HttpResponseRedirect, Http404, HttpResponse
from django.utils import simplejson as json
from django.utils.datastructures import SortedDict
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
	
	def get_weighted_results(self, threshhold=None):
		"Returns this search's results ordered by decreasing weight."
		if not hasattr(self, '_weighted_results'):
			result_qs = self.result_urls.all()
			
			if threshhold is not None:
				result_qs = result_qs.filter(counts__datetime__gte=threshhold)
			
			results = [result for result in result_qs]
			
			results.sort(cmp=lambda x,y: cmp(y.weight, x.weight))
			
			self._weighted_results = results
		
		return self._weighted_results
	
	def get_favored_results(self, error=5, threshhold=None):
		"""
		Calculate the set of most-favored results. A higher error
		will cause this method to be more reticent about adding new
		items.
		
		The thought is to see whether there are any results which
		vastly outstrip the other options. As such, evenly-weighted
		results should be grouped together and either added or
		excluded as a group.
		"""
		if not hasattr(self, '_favored_results'):
			results = self.get_weighted_results(threshhold)
			
			grouped_results = SortedDict()
			
			for result in results:
				grouped_results.setdefault(result.weight, []).append(result)
			
			self._favored_results = []
			
			for value, subresults in grouped_results.items():
				cost = error * sum([(value - result.weight)**2 for result in self._favored_results])
				if value > cost:
					self._favored_results += subresults
				else:
					break
		return self._favored_results
	
	class Meta:
		ordering = ['string']
		verbose_name_plural = 'searches'


class ResultURL(models.Model):
	search = models.ForeignKey(Search, related_name='result_urls')
	url = models.TextField(validators=[RedirectValidator()])
	
	def __unicode__(self):
		return self.url
	
	def get_weight(self, threshhold=None):
		if not hasattr(self, '_weight'):
			clicks = self.clicks.all()
			
			if threshhold is not None:
				clicks = clicks.filter(datetime__gte=threshhold)
			
			self._weight = sum([click.weight for click in clicks])
		
		return self._weight
	weight = property(get_weight)
	
	class Meta:
		ordering = ['url']


class Click(models.Model):
	result = models.ForeignKey(ResultURL, related_name='clicks')
	datetime = models.DateTimeField()
	
	def __unicode__(self):
		return self.datetime.strftime('%B %d, %Y %H:%M:%S')
	
	def get_weight(self, default=1, weighted=lambda value, days: value/days**2):
		if not hasattr(self, '_weight'):
			days = (datetime.datetime.now() - self.datetime).days
			if days < 0:
				raise ValueError("Click dates must be in the past.")
			default = float(default)
			if days == 0:
				self._weight = float(default)
			else:
				self._weight = weighted(default, days)
		return self._weight
	weight = property(get_weight)
	
	def clean(self):
		if self.datetime > datetime.datetime.now():
			raise ValidationError("Click dates must be in the past.")
	
	class Meta:
		ordering = ['datetime']
		get_latest_by = 'datetime'


class SearchView(MultiView):
	results_page = models.ForeignKey(Page, related_name='search_results_related')
	searches = SlugMultipleChoiceField(choices=registry.iterchoices())
	enable_ajax_api = models.BooleanField("Enable AJAX API", default=True)
	placeholder_text = models.CharField(max_length=75, default="Search")
	
	search_form = SearchForm
	
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
				url(r'^(?P<slug>[\w-]+)$', self.ajax_api_view, name='ajax_api_view')
			)
		return urlpatterns
	
	def get_search_instance(self, slug, search_string):
		return registry[slug](search_string.lower())
	
	def results_view(self, request, extra_context=None):
		results = None
		
		context = self.get_context()
		context.update(extra_context or {})
		
		if SEARCH_ARG_GET_KEY in request.GET:
			form = self.search_form(request.GET)
			
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
					context.update({
						'searches': [{'verbose_name': verbose_name, 'url': self.reverse('ajax_api_view', kwargs={'slug': slug}, node=request.node)} for slug, verbose_name in registry.iterchoices()]
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
		response = HttpResponse(json.dumps({
			'results': [result.get_context() for result in search_instance.results],
		}))
		return response