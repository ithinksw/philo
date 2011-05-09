#encoding: utf-8
import datetime

from django.conf import settings
from django.contrib.sites.models import Site
from django.core.cache import cache
from django.db.models.options import get_verbose_name as convert_camelcase
from django.utils import simplejson as json
from django.utils.http import urlquote_plus
from django.utils.safestring import mark_safe
from django.utils.text import capfirst
from django.template import loader, Context, Template

from philo.contrib.sobol.utils import make_tracking_querydict


if getattr(settings, 'SOBOL_USE_EVENTLET', False):
	try:
		from eventlet.green import urllib2
	except:
		import urllib2
else:
	import urllib2


__all__ = (
	'Result', 'BaseSearch', 'DatabaseSearch', 'URLSearch', 'JSONSearch', 'GoogleSearch', 'registry'
)


SEARCH_CACHE_KEY = 'philo_sobol_search_results'
DEFAULT_RESULT_TEMPLATE_STRING = "{% if url %}<a href='{{ url }}'>{% endif %}{{ title }}{% if url %}</a>{% endif %}"
DEFAULT_RESULT_TEMPLATE = Template(DEFAULT_RESULT_TEMPLATE_STRING)

# Determines the timeout on the entire result cache.
MAX_CACHE_TIMEOUT = 60*24*7


class RegistrationError(Exception):
	pass


class SearchRegistry(object):
	# Holds a registry of search types by slug.
	def __init__(self):
		self._registry = {}
	
	def register(self, search, slug=None):
		slug = slug or search.slug
		if slug in self._registry:
			registered = self._registry[slug]
			if registered.__module__ != search.__module__:
				raise RegistrationError("A different search is already registered as `%s`" % slug)
		else:
			self._registry[slug] = search
	
	def unregister(self, search, slug=None):
		if slug is not None:
			if slug in self._registry and self._registry[slug] == search:
				del self._registry[slug]
			raise RegistrationError("`%s` is not registered as `%s`" % (search, slug))
		else:
			for slug, search in self._registry.items():
				if search == search:
					del self._registry[slug]
	
	def items(self):
		return self._registry.items()
	
	def iteritems(self):
		return self._registry.iteritems()
	
	def iterchoices(self):
		for slug, search in self.iteritems():
			yield slug, search.verbose_name
	
	def __getitem__(self, key):
		return self._registry[key]
	
	def __iter__(self):
		return self._registry.__iter__()


registry = SearchRegistry()


class Result(object):
	"""
	A result is instantiated with a configuration dictionary, a search,
	and a template name. The configuration dictionary is expected to
	define a `title` and optionally a `url`. Any other variables may be
	defined; they will be made available through the result object in
	the template, if one is defined.
	"""
	def __init__(self, search, result):
		self.search = search
		self.result = result
	
	def get_title(self):
		return self.search.get_result_title(self.result)
	
	def get_url(self):
		qd = self.search.get_result_querydict(self.result)
		if qd is None:
			return ""
		return "?%s" % qd.urlencode()
	
	def get_template(self):
		return self.search.get_result_template(self.result)
	
	def get_extra_context(self):
		return self.search.get_result_extra_context(self.result)
	
	def get_context(self):
		context = self.get_extra_context()
		context.update({
			'title': self.get_title(),
			'url': self.get_url()
		})
		return context
	
	def render(self):
		t = self.get_template()
		c = Context(self.get_context())
		return t.render(c)
	
	def __unicode__(self):
		return self.render()


class BaseSearchMetaclass(type):
	def __new__(cls, name, bases, attrs):
		if 'verbose_name' not in attrs:
			attrs['verbose_name'] = capfirst(convert_camelcase(name))
		if 'slug' not in attrs:
			attrs['slug'] = name.lower()
		return super(BaseSearchMetaclass, cls).__new__(cls, name, bases, attrs)


class BaseSearch(object):
	"""
	Defines a generic search interface. Accessing self.results will
	attempt to retrieve cached results and, if that fails, will
	initiate a new search and store the results in the cache.
	"""
	__metaclass__ = BaseSearchMetaclass
	result_limit = 10
	_cache_timeout = 60*48
	
	def __init__(self, search_arg):
		self.search_arg = search_arg
	
	def _get_cached_results(self):
		"""Return the cached results if the results haven't timed out. Otherwise return None."""
		result_cache = cache.get(SEARCH_CACHE_KEY)
		if result_cache and self.__class__ in result_cache and self.search_arg.lower() in result_cache[self.__class__]:
			cached = result_cache[self.__class__][self.search_arg.lower()]
			if cached['timeout'] >= datetime.datetime.now():
				return cached['results']
		return None
	
	def _set_cached_results(self, results, timeout):
		"""Sets the results to the cache for <timeout> minutes."""
		result_cache = cache.get(SEARCH_CACHE_KEY) or {}
		cached = result_cache.setdefault(self.__class__, {}).setdefault(self.search_arg.lower(), {})
		cached.update({
			'results': results,
			'timeout': datetime.datetime.now() + datetime.timedelta(minutes=timeout)
		})
		cache.set(SEARCH_CACHE_KEY, result_cache, MAX_CACHE_TIMEOUT)
	
	@property
	def results(self):
		if not hasattr(self, '_results'):
			results = self._get_cached_results()
			if results is None:
				try:
					# Cache one extra result so we can see if there are
					# more results to be had.
					limit = self.result_limit
					if limit is not None:
						limit += 1
					results = self.get_results(limit)
				except:
					if settings.DEBUG:
						raise
					#  On exceptions, don't set any cache; just return.
					return []
			
				self._set_cached_results(results, self._cache_timeout)
			self._results = results
		
		return self._results
	
	def get_results(self, limit=None, result_class=Result):
		"""
		Calls self.search() and parses the return value into Result objects.
		"""
		results = self.search(limit)
		return [result_class(self, result) for result in results]
	
	def search(self, limit=None):
		"""
		Returns an iterable of up to <limit> results. The
		get_result_title, get_result_url, get_result_template, and
		get_result_extra_context methods will be used to interpret the
		individual items that this function returns, so the result can
		be an object with attributes as easily as a dictionary
 		with keys. The only restriction is that the objects be
		pickleable so that they can be used with django's cache system.
		"""
		raise NotImplementedError
	
	def get_result_title(self, result):
		raise NotImplementedError
	
	def get_result_url(self, result):
		"Subclasses override this to provide the actual URL for the result."
		raise NotImplementedError
	
	def get_result_querydict(self, result):
		url = self.get_result_url(result)
		if url is None:
			return None
		return make_tracking_querydict(self.search_arg, url)
	
	def get_result_template(self, result):
		if hasattr(self, 'result_template'):
			return loader.get_template(self.result_template)
		if not hasattr(self, '_result_template'):
			self._result_template = DEFAULT_RESULT_TEMPLATE
		return self._result_template
	
	def get_result_extra_context(self, result):
		return {}
	
	def has_more_results(self):
		"""Useful to determine whether to display a `view more results` link."""
		return len(self.results) > self.result_limit
	
	@property
	def more_results_url(self):
		"""
		Returns the actual url for more results. This will be encoded
		into a querystring for tracking purposes.
		"""
		raise NotImplementedError
	
	@property
	def more_results_querydict(self):
		return make_tracking_querydict(self.search_arg, self.more_results_url)
	
	def __unicode__(self):
		return ' '.join(self.__class__.verbose_name.rsplit(' ', 1)[:-1]) + ' results'


class DatabaseSearch(BaseSearch):
	model = None
	
	def search(self, limit=None):
		if not hasattr(self, '_qs'):
			self._qs = self.get_queryset()
			if limit is not None:
				self._qs = self._qs[:limit]
		
		return self._qs
	
	def get_queryset(self):
		return self.model._default_manager.all()


class URLSearch(BaseSearch):
	"""
	Defines a generic interface for searches that require accessing a
	certain url to get search results.
	"""
	search_url = ''
	query_format_str = "%s"

	@property
	def url(self):
		"The URL where the search gets its results."
		return self.search_url + self.query_format_str % urlquote_plus(self.search_arg)

	@property
	def more_results_url(self):
		"The URL where the users would go to get more results."
		return self.url
	
	def parse_response(self, response, limit=None):
		raise NotImplementedError
	
	def search(self, limit=None):
		return self.parse_response(urllib2.urlopen(self.url), limit=limit)


class JSONSearch(URLSearch):
	"""
	Makes a GET request and parses the results as JSON. The default
	behavior assumes that the return value is a list of results.
	"""
	def parse_response(self, response, limit=None):
		return json.loads(response.read())[:limit]


class GoogleSearch(JSONSearch):
	search_url = "http://ajax.googleapis.com/ajax/services/search/web"
	# TODO: Change this template to reflect the app's actual name.
	result_template = 'search/googlesearch.html'
	_cache_timeout = 60
	verbose_name = "Google search (current site)"
	
	@property
	def query_format_str(self):
		default_args = self.default_args
		if default_args:
			default_args += " "
		return "?v=1.0&q=%s%%s" % urlquote_plus(default_args).replace('%', '%%')
	
	@property
	def default_args(self):
		return "site:%s" % Site.objects.get_current().domain
	
	def parse_response(self, response, limit=None):
		responseData = json.loads(response.read())['responseData']
		results, cursor = responseData['results'], responseData['cursor']
		
		if results:
			self._more_results_url = cursor['moreResultsUrl']
			self._estimated_result_count = cursor['estimatedResultCount']
		
		return results[:limit]
	
	@property
	def url(self):
		# Google requires that an ajax request have a proper Referer header.
		return urllib2.Request(
			super(GoogleSearch, self).url,
			None,
			{'Referer': "http://%s" % Site.objects.get_current().domain}
		)
	
	@property
	def has_more_results(self):
		if self.results and len(self.results) < self._estimated_result_count:
			return True
		return False
	
	@property
	def more_results_url(self):
		return self._more_results_url
	
	def get_result_title(self, result):
		return result['titleNoFormatting']
	
	def get_result_url(self, result):
		return result['unescapedUrl']
	
	def get_result_extra_context(self, result):
		return result


registry.register(GoogleSearch)


try:
	from BeautifulSoup import BeautifulSoup, SoupStrainer, BeautifulStoneSoup
except:
	pass
else:
	__all__ += ('ScrapeSearch', 'XMLSearch',)
	class ScrapeSearch(URLSearch):
		_strainer_args = []
		_strainer_kwargs = {}
		
		@property
		def strainer(self):
			if not hasattr(self, '_strainer'):
				self._strainer = SoupStrainer(*self._strainer_args, **self._strainer_kwargs)
			return self._strainer
		
		def parse_response(self, response, limit=None):
			strainer = self.strainer
			soup = BeautifulSoup(response, parseOnlyThese=strainer)
			return self.parse_results(soup.findAll(recursive=False, limit=limit))
		
		def parse_results(self, results):
			"""
			Provides a hook for parsing the results of straining. This
			has no default behavior because the results absolutely
			must be parsed to properly extract the information.
			For more information, see http://www.crummy.com/software/BeautifulSoup/documentation.html#Improving%20Memory%20Usage%20with%20extract
			"""
			raise NotImplementedError
	
	
	class XMLSearch(ScrapeSearch):
		_self_closing_tags = []
		
		def parse_response(self, response, limit=None):
			strainer = self.strainer
			soup = BeautifulStoneSoup(response, selfClosingTags=self._self_closing_tags, parseOnlyThese=strainer)
			return self.parse_results(soup.findAll(recursive=False, limit=limit))