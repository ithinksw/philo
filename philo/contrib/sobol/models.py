import datetime
import itertools

from django.conf import settings
from django.conf.urls.defaults import patterns, url
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.db import models
from django.http import HttpResponseRedirect, Http404, HttpResponse
from django.utils import simplejson as json
from django.utils.datastructures import SortedDict

from philo.contrib.sobol import registry, get_search_instance
from philo.contrib.sobol.forms import SearchForm
from philo.contrib.sobol.utils import HASH_REDIRECT_GET_KEY, URL_REDIRECT_GET_KEY, SEARCH_ARG_GET_KEY, check_redirect_hash, RegistryIterator
from philo.exceptions import ViewCanNotProvideSubpath
from philo.models import MultiView, Page
from philo.models.fields import SlugMultipleChoiceField

eventlet = None
if getattr(settings, 'SOBOL_USE_EVENTLET', False):
	try:
		import eventlet
	except:
		pass


class Search(models.Model):
	"""Represents all attempts to search for a unique string."""
	#: The string which was searched for.
	string = models.TextField()
	
	def __unicode__(self):
		return self.string
	
	def get_weighted_results(self, threshhold=None):
		"""
		Returns a list of :class:`ResultURL` instances related to the search and ordered by decreasing weight. This will be cached on the instance.
		
		:param threshhold: The earliest datetime that a :class:`Click` can have been made on a related :class:`ResultURL` in order to be included in the weighted results (or ``None`` to include all :class:`Click`\ s and :class:`ResultURL`\ s).
		
		"""
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
		Calculates the set of most-favored results based on their weight. Evenly-weighted results will be grouped together and either added or excluded as a group.
		
		:param error: An arbitrary number; higher values will cause this method to be more reticent about adding new items to the favored results.
		:param threshhold: Will be passed directly into :meth:`get_weighted_results`
		
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
			if len(self._favored_results) == len(results):
				self._favored_results = []
		return self._favored_results
	
	class Meta:
		ordering = ['string']
		verbose_name_plural = 'searches'


class ResultURL(models.Model):
	"""Represents a URL which has been selected one or more times for a :class:`Search`."""
	#: A :class:`ForeignKey` to the :class:`Search` which the :class:`ResultURL` is related to.
	search = models.ForeignKey(Search, related_name='result_urls')
	#: The URL which was selected.
	url = models.TextField(validators=[URLValidator()])
	
	def __unicode__(self):
		return self.url
	
	def get_weight(self, threshhold=None):
		"""
		Calculates, caches, and returns the weight of the :class:`ResultURL`.
		
		:param threshhold: The datetime limit before which :class:`Click`\ s will not contribute to the weight of the :class:`ResultURL`.
		
		"""
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
	"""Represents a click on a :class:`ResultURL`."""
	#: A :class:`ForeignKey` to the :class:`ResultURL` which the :class:`Click` is related to.
	result = models.ForeignKey(ResultURL, related_name='clicks')
	#: The datetime when the click was registered in the system.
	datetime = models.DateTimeField()
	
	def __unicode__(self):
		return self.datetime.strftime('%B %d, %Y %H:%M:%S')
	
	def get_weight(self, default=1, weighted=lambda value, days: value/days**2):
		"""Calculates and returns the weight of the :class:`Click`."""
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


try:
	from south.modelsinspector import add_introspection_rules
except ImportError:
	pass
else:
	add_introspection_rules([], ["^philo\.contrib\.sobol\.models\.RegistryChoiceField"])


class SearchView(MultiView):
	"""Handles a view for the results of a search, anonymously tracks the selections made by end users, and provides an AJAX API for asynchronous search result loading. This can be particularly useful if some searches are slow."""
	#: :class:`ForeignKey` to a :class:`.Page` which will be used to render the search results.
	results_page = models.ForeignKey(Page, related_name='search_results_related')
	#: A :class:`.SlugMultipleChoiceField` whose choices are the contents of :obj:`.sobol.search.registry`
	searches = SlugMultipleChoiceField(choices=registry.iterchoices())
	#: A :class:`BooleanField` which controls whether or not the AJAX API is enabled.
	#:
	#: .. note:: If the AJAX API is enabled, a ``ajax_api_url`` attribute will be added to each search instance containing the url and get parameters for an AJAX request to retrieve results for that search.
	#:
	#: .. note:: Be careful not to access :attr:`search_instance.results <.BaseSearch.results>` if the AJAX API is enabled - otherwise the search will be run immediately rather than on the AJAX request.
	enable_ajax_api = models.BooleanField("Enable AJAX API", default=True)
	#: A :class:`CharField` containing the placeholder text which is intended to be used for the search box for the :class:`SearchView`. It is the template author's responsibility to make use of this information.
	placeholder_text = models.CharField(max_length=75, default="Search")
	
	#: The form which will be used to validate the input to the search box for this :class:`SearchView`.
	search_form = SearchForm
	
	def __unicode__(self):
		return u"%s (%s)" % (self.placeholder_text, u", ".join([display for slug, display in registry.iterchoices() if slug in self.searches]))
	
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
	
	def results_view(self, request, extra_context=None):
		"""
		Renders :attr:`results_page` with a context containing an instance of :attr:`search_form`. If the form was submitted and was valid, then one of two things has happened:
		
		* A search has been initiated. In this case, a list of search instances will be added to the context as ``searches``. If :attr:`enable_ajax_api` is enabled, each instance will have an ``ajax_api_url`` attribute containing the url needed to make an AJAX request for the search results.
		* A link has been chosen. In this case, corresponding :class:`Search`, :class:`ResultURL`, and :class:`Click` instances will be created and the user will be redirected to the link's actual url.
		
		"""
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
				
				search_instances = []
				for slug in self.searches:
					if slug in registry:
						search_instance = get_search_instance(slug, search_string)
						search_instances.append(search_instance)
					
						if self.enable_ajax_api:
							search_instance.ajax_api_url = "%s?%s=%s" % (self.reverse('ajax_api_view', kwargs={'slug': slug}, node=request.node), SEARCH_ARG_GET_KEY, search_string)
				
				if eventlet and not self.enable_ajax_api:
					pool = eventlet.GreenPool()
					for instance in search_instances:
						pool.spawn_n(lambda x: x.results, search_instance)
					pool.waitall()
				
				context.update({
					'searches': search_instances,
					'favored_results': []
				})
				
				try:
					search = Search.objects.get(string=search_string)
				except Search.DoesNotExist:
					pass
				else:
					context['favored_results'] = [r.url for r in search.get_favored_results()]
		else:
			form = SearchForm()
		
		context.update({
			'form': form
		})
		return self.results_page.render_to_response(request, extra_context=context)
	
	def ajax_api_view(self, request, slug, extra_context=None):
		"""
		Returns a JSON object containing the following variables:
		
		search
			Contains the slug for the search.
		results
			Contains the results of :meth:`.Result.get_context` for each result.
		rendered
			Contains the results of :meth:`.Result.render` for each result.
		hasMoreResults
			``True`` or ``False`` whether the search has more results according to :meth:`BaseSearch.has_more_results`
		moreResultsURL
			Contains ``None`` or a querystring which, once accessed, will note the :class:`Click` and redirect the user to a page containing more results.
		
		"""
		search_string = request.GET.get(SEARCH_ARG_GET_KEY)
		
		if not request.is_ajax() or not self.enable_ajax_api or slug not in registry or slug not in self.searches or search_string is None:
			raise Http404
		
		search_instance = get_search_instance(slug, search_string)
		
		return HttpResponse(json.dumps({
			'search': search_instance.slug,
			'results': [result.get_context() for result in search_instance.results],
			'hasMoreResults': search_instance.has_more_results,
			'moreResultsURL': search_instance.more_results_url,
		}), mimetype="application/json")