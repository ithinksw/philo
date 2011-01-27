from django.conf.urls.defaults import patterns, url
from django.contrib import messages
from django.db import models
from django.http import HttpResponseRedirect, Http404
from django.utils import simplejson as json
from philo.contrib.sobol import registry
from philo.contrib.sobol.forms import SearchForm
from philo.contrib.sobol.utils import HASH_REDIRECT_GET_KEY, URL_REDIRECT_GET_KEY, SEARCH_ARG_GET_KEY, check_redirect_hash
from philo.exceptions import ViewCanNotProvideSubpath
from philo.models import MultiView, Page, SlugMultipleChoiceField
from philo.validators import RedirectValidator
import datetime
try:
	import eventlet
except:
	eventlet = False


class Search(models.Model):
	string = models.TextField()
	
	def __unicode__(self):
		return self.search_string
	
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
	allow_partial_loading = models.BooleanField(default=True)
	placeholder_text = models.CharField(max_length=75, default="Search")
	
	def get_reverse_params(self, obj):
		raise ViewCanNotProvideSubpath
	
	@property
	def urlpatterns(self):
		urlpatterns = patterns('',
			url(r'^$', self.results_view, name='results'),
		)
		if self.allow_partial_loading:
			urlpatterns += patterns('',
				url(r'^(?P<slug>[\w-]+)/?', self.partial_ajax_results_view, name='partial_ajax_results_view')
			)
		return urlpatterns
	
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
				if not self.allow_partial_loading:
					search_instances = []
					if eventlet:
						pool = eventlet.GreenPool()
					for slug in self.searches:
						search = registry[slug]
						search_instance = search(search_string)
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
	
	def partial_ajax_results_view(self, request, slug, extra_context=None):
		search_string = request.GET.get(SEARCH_ARG_GET_KEY)
		
		if not request.is_ajax() or not self.allow_partial_loading or slug not in self.searches or search_string is None:
			raise Http404
		
		search = registry[slug]
		search_instance = search(search_string.lower())
		results = search_instance.results
		response = json.dumps({
			'results': results,
			'template': search_instance.get_ajax_result_template()
		})
		return response