#encoding: utf-8
import datetime
from hashlib import sha1

from django.conf import settings
from django.contrib.sites.models import Site
from django.core.cache import cache
from django.db.models.options import get_verbose_name as convert_camelcase
from django.utils import simplejson as json
from django.utils.http import urlquote_plus
from django.utils.safestring import mark_safe
from django.utils.text import capfirst
from django.template import loader, Context, Template, TemplateDoesNotExist

from philo.contrib.sobol.utils import make_tracking_querydict
from philo.utils.registry import Registry


if getattr(settings, 'SOBOL_USE_EVENTLET', False):
	try:
		from eventlet.green import urllib2
	except:
		import urllib2
else:
	import urllib2


__all__ = (
	'Result', 'BaseSearch', 'DatabaseSearch', 'URLSearch', 'JSONSearch', 'GoogleSearch', 'registry', 'get_search_instance'
)


SEARCH_CACHE_SEED = 'philo_sobol_search_results'
USE_CACHE = getattr(settings, 'SOBOL_USE_CACHE', True)


#: A registry for :class:`BaseSearch` subclasses that should be available in the admin.
registry = Registry()


def _make_cache_key(search, search_arg):
	return sha1(SEARCH_CACHE_SEED + search.slug + search_arg).hexdigest()


def get_search_instance(slug, search_arg):
	"""Returns a search instance for the given slug, either from the cache or newly-instantiated."""
	search = registry[slug]
	search_arg = search_arg.lower()
	if USE_CACHE:
		key = _make_cache_key(search, search_arg)
		cached = cache.get(key)
		if cached:
			return cached
	instance = search(search_arg)
	instance.slug = slug
	return instance


class Result(object):
	"""
	:class:`Result` is a helper class that, given a search and a result of that search, is able to correctly render itself with a template defined by the search. Every :class:`Result` will pass a ``title``, a ``url`` (if applicable), and the raw ``result`` returned by the search into the template context when rendering.
	
	:param search: An instance of a :class:`BaseSearch` subclass or an object that implements the same API.
	:param result: An arbitrary result from the ``search``.
	
	"""
	def __init__(self, search, result):
		self.search = search
		self.result = result
	
	def get_title(self):
		"""Returns the title of the result by calling :meth:`BaseSearch.get_result_title` on the raw result."""
		return self.search.get_result_title(self.result)
	
	def get_url(self):
		"""Returns the url of the result or ``None`` by calling :meth:`BaseSearch.get_result_url` on the raw result. This url will contain a querystring which, if used, will track a :class:`.Click` for the actual url."""
		return self.search.get_result_url(self.result)
	
	def get_actual_url(self):
		"""Returns the actual url of the result by calling :meth:`BaseSearch.get_actual_result_url` on the raw result."""
		return self.search.get_actual_result_url(self.result)
	
	def get_content(self):
		"""Returns the content of the result by calling :meth:`BaseSearch.get_result_content` on the raw result."""
		return self.search.get_result_content(self.result)
	
	def get_template(self):
		"""Returns the template which will be used to render the :class:`Result` by calling :meth:`BaseSearch.get_result_template` on the raw result."""
		return self.search.get_result_template(self.result)
	
	def get_context(self):
		"""
		Returns the context dictionary for the result. This is used both in rendering the result and in the AJAX return value for :meth:`.SearchView.ajax_api_view`. The context will contain the following keys:
		
		title
			The result of calling :meth:`get_title`
		url
			The result of calling :meth:`get_url`
		content
			The result of calling :meth:`get_content`
		
		"""
		if not hasattr(self, '_context'):
			self._context = {
				'title': self.get_title(),
				'url': self.get_url(),
				'actual_url': self.get_actual_url(),
				'content': self.get_content()
			}
		return self._context
	
	def render(self):
		"""Returns the template from :meth:`get_template` rendered with the context from :meth:`get_context`."""
		t = self.get_template()
		c = Context(self.get_context())
		return t.render(c)
	
	def __unicode__(self):
		"""Returns :meth:`render`"""
		return self.render()


class BaseSearchMetaclass(type):
	def __new__(cls, name, bases, attrs):
		if 'verbose_name' not in attrs:
			attrs['verbose_name'] = capfirst(' '.join(convert_camelcase(name).rsplit(' ', 1)[:-1]))
		if 'slug' not in attrs:
			attrs['slug'] = name[:-6].lower() if name.endswith("Search") else name.lower()
		return super(BaseSearchMetaclass, cls).__new__(cls, name, bases, attrs)


class BaseSearch(object):
	"""
	Defines a generic search api. Accessing :attr:`results` will attempt to retrieve cached results and, if that fails, will initiate a new search and store the results in the cache. Each search has a ``verbose_name`` and a ``slug``. If these are not provided as attributes, they will be automatically generated based on the name of the class.
	
	:param search_arg: The string which is being searched for.
	
	"""
	__metaclass__ = BaseSearchMetaclass
	#: The number of results to return from the complete list. Default: 5
	result_limit = 5
	#: How long the items for the search should be cached (in minutes). Default: 48 hours.
	_cache_timeout = 60*48
	#: The path to the template which will be used to render the :class:`Result`\ s for this search. If this is ``None``, then the framework will try ``sobol/search/<slug>/result.html`` and ``sobol/search/result.html``.
	result_template = None
	#: The path to the template which will be used to generate the title of the :class:`Result`\ s for this search. If this is ``None``, then the framework will try ``sobol/search/<slug>/title.html`` and ``sobol/search/title.html``.
	title_template = None
	#: The path to the template which will be used to generate the content of the :class:`Result`\ s for this search. If this is ``None``, then the framework will try ``sobol/search/<slug>/content.html`` and ``sobol/search/content.html``.
	content_template = None
	
	def __init__(self, search_arg):
		self.search_arg = search_arg
	
	@property
	def results(self):
		"""Retrieves cached results or initiates a new search via :meth:`get_results` and caches the results."""
		if not hasattr(self, '_results'):
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
			
			self._results = results
			
			if USE_CACHE:
				for result in results:
					result.get_context()
				key = _make_cache_key(self, self.search_arg)
				cache.set(key, self, self._cache_timeout)
		
		return self._results
	
	def get_results(self, limit=None, result_class=Result):
		"""
		Calls :meth:`search` and parses the return value into :class:`Result` instances.
		
		:param limit: Passed directly to :meth:`search`.
		:param result_class: The class used to represent the results. This will be instantiated with the :class:`BaseSearch` instance and the raw result from the search.
		
		"""
		results = self.search(limit)
		return [result_class(self, result) for result in results]
	
	def search(self, limit=None):
		"""Returns an iterable of up to ``limit`` results. The :meth:`get_result_title`, :meth:`get_result_url`, :meth:`get_result_template`, and :meth:`get_result_extra_context` methods will be used to interpret the individual items that this function returns, so the result can be an object with attributes as easily as a dictionary with keys. However, keep in mind that the raw results will be stored with django's caching mechanisms and will be converted to JSON."""
		raise NotImplementedError
	
	def get_actual_result_url(self, result):
		"""Returns the actual URL for the ``result`` or ``None`` if there is no URL. Must be implemented by subclasses."""
		raise NotImplementedError
	
	def get_result_querydict(self, result):
		"""Returns a querydict for tracking selection of the result, or ``None`` if there is no URL for the result."""
		url = self.get_actual_result_url(result)
		if url is None:
			return None
		return make_tracking_querydict(self.search_arg, url)
	
	def get_result_url(self, result):
		"""Returns ``None`` or a url which, when accessed, will register a :class:`.Click` for that url."""
		qd = self.get_result_querydict(result)
		if qd is None:
			return None
		return "?%s" % qd.urlencode()
	
	def get_result_title(self, result):
		"""Returns the title of the ``result``. By default, renders ``sobol/search/<slug>/title.html`` or ``sobol/search/title.html`` with the result in the context. This can be overridden by setting :attr:`title_template` or simply overriding :meth:`get_result_title`. If no template can be found, this will raise :exc:`TemplateDoesNotExist`."""
		return loader.render_to_string(self.title_template or [
			'sobol/search/%s/title.html' % self.slug,
			'sobol/search/title.html'
		], {'result': result})
	
	def get_result_content(self, result):
		"""Returns the content for the ``result``. By default, renders ``sobol/search/<slug>/content.html`` or ``sobol/search/content.html`` with the result in the context. This can be overridden by setting :attr:`content_template` or simply overriding :meth:`get_result_content`. If no template is found, this will return an empty string."""
		try:
			return loader.render_to_string(self.content_template or [
				'sobol/search/%s/content.html' % self.slug,
				'sobol/search/content.html'
			], {'result': result})
		except TemplateDoesNotExist:
			return ""
	
	def get_result_template(self, result):
		"""Returns the template to be used for rendering the ``result``. For a search with slug ``google``, this would first try ``sobol/search/google/result.html``, then fall back on ``sobol/search/result.html``. Subclasses can override this by setting :attr:`result_template` to the path of another template."""
		if self.result_template:
			return loader.get_template(self.result_template)
		return loader.select_template([
			'sobol/search/%s/result.html' % self.slug,
			'sobol/search/result.html'
		])
	
	@property
	def has_more_results(self):
		"""Returns ``True`` if there are more results than :attr:`result_limit` and ``False`` otherwise."""
		return len(self.results) > self.result_limit
	
	def get_actual_more_results_url(self):
		"""Returns the actual url for more results. By default, simply returns ``None``."""
		return None
	
	def get_more_results_querydict(self):
		"""Returns a :class:`QueryDict` for tracking whether people click on a 'more results' link."""
		url = self.get_actual_more_results_url()
		if url:
			return make_tracking_querydict(self.search_arg, url)
		return None
	
	@property
	def more_results_url(self):
		"""Returns a URL which consists of a querystring which, when accessed, will log a :class:`.Click` for the actual URL."""
		qd = self.get_more_results_querydict()
		if qd is None:
			return None
		return "?%s" % qd.urlencode()
	
	def __unicode__(self):
		return self.verbose_name


class DatabaseSearch(BaseSearch):
	"""Implements :meth:`~BaseSearch.search` and :meth:`get_queryset` methods to handle database queries."""
	#: The model which should be searched by the :class:`DatabaseSearch`.
	model = None
	
	def search(self, limit=None):
		if not hasattr(self, '_qs'):
			self._qs = self.get_queryset()
			if limit is not None:
				self._qs = self._qs[:limit]
		
		return self._qs
	
	def get_queryset(self):
		"""Returns a :class:`QuerySet` of all instances of :attr:`model`. This method should be overridden by subclasses to specify how the search should actually be implemented for the model."""
		return self.model._default_manager.all()


class URLSearch(BaseSearch):
	"""Defines a generic interface for searches that require accessing a certain url to get search results."""
	#: The base URL which will be accessed to get the search results.
	search_url = ''
	#: The url-encoded query string to be used for fetching search results from :attr:`search_url`. Must have one ``%s`` to contain the search argument.
	query_format_str = "%s"

	@property
	def url(self):
		"""The URL where the search gets its results. Composed from :attr:`search_url` and :attr:`query_format_str`."""
		return self.search_url + self.query_format_str % urlquote_plus(self.search_arg)
	
	def get_actual_more_results_url(self):
		return self.url
	
	def parse_response(self, response, limit=None):
		"""Handles the ``response`` from accessing :attr:`url` (with :func:`urllib2.urlopen`) and returns a list of up to ``limit`` results."""
		raise NotImplementedError
	
	def search(self, limit=None):
		return self.parse_response(urllib2.urlopen(self.url), limit=limit)


class JSONSearch(URLSearch):
	"""Makes a GET request and parses the results as JSON. The default behavior assumes that the response contains a list of results."""
	def parse_response(self, response, limit=None):
		return json.loads(response.read())[:limit]


class GoogleSearch(JSONSearch):
	"""An example implementation of a :class:`JSONSearch`."""
	search_url = "http://ajax.googleapis.com/ajax/services/search/web"
	_cache_timeout = 60
	verbose_name = "Google search (current site)"
	_more_results_url = None
	
	@property
	def query_format_str(self):
		default_args = self.default_args
		if default_args:
			default_args += " "
		return "?v=1.0&q=%s%%s" % urlquote_plus(default_args).replace('%', '%%')
	
	@property
	def default_args(self):
		"""Unquoted default arguments for the :class:`GoogleSearch`."""
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
	
	def get_actual_more_results_url(self):
		return self._more_results_url
	
	def get_actual_result_url(self, result):
		return result['unescapedUrl']
	
	def get_result_title(self, result):
		return mark_safe(result['titleNoFormatting'])
	
	def get_result_content(self, result):
		return mark_safe(result['content'])


registry.register(GoogleSearch)


try:
	from BeautifulSoup import BeautifulSoup, SoupStrainer, BeautifulStoneSoup
except:
	pass
else:
	__all__ += ('ScrapeSearch', 'XMLSearch',)
	class ScrapeSearch(URLSearch):
		"""A base class for scrape-style searching, available if :mod:`BeautifulSoup` is installed."""
		#: Arguments to be passed into a :class:`SoupStrainer`.
		strainer_args = []
		#: Keyword arguments to be passed into a :class:`SoupStrainer`.
		strainer_kwargs = {}
		
		@property
		def strainer(self):
			"""
			Caches and returns a :class:`SoupStrainer` initialized with :attr:`strainer_args` and :attr:`strainer_kwargs`. This strainer will be used to parse only certain parts of the document.
			
			.. seealso:: `BeautifulSoup: Improving Performance by Parsing Only Part of the Document <http://www.crummy.com/software/BeautifulSoup/documentation.html#Improving%20Performance%20by%20Parsing%20Only%20Part%20of%20the%20Document>`_
			
			"""
			if not hasattr(self, '_strainer'):
				self._strainer = SoupStrainer(*self.strainer_args, **self.strainer_kwargs)
			return self._strainer
		
		def parse_response(self, response, limit=None):
			strainer = self.strainer
			soup = BeautifulSoup(response, parseOnlyThese=strainer)
			return self.parse_results(soup.findAll(recursive=False, limit=limit))
		
		def parse_results(self, results):
			"""
			Provides a hook for parsing the results of straining. This has no default behavior and must be implemented by subclasses because the results absolutely must be parsed to properly extract the information.
			
			.. seealso:: `BeautifulSoup: Improving Memory Usage with extract <http://www.crummy.com/software/BeautifulSoup/documentation.html#Improving%20Memory%20Usage%20with%20extract>`_
			"""
			raise NotImplementedError
	
	
	class XMLSearch(ScrapeSearch):
		"""A base class for searching XML results."""
		#: Self-closing tag names to be used when interpreting the XML document
		#:
		#: .. seealso:: `BeautifulSoup: Parsing XML <http://www.crummy.com/software/BeautifulSoup/documentation.html#Parsing%20XML>`_
		self_closing_tags = []
		
		def parse_response(self, response, limit=None):
			strainer = self.strainer
			soup = BeautifulStoneSoup(response, selfClosingTags=self.self_closing_tags, parseOnlyThese=strainer)
			return self.parse_results(soup.findAll(recursive=False, limit=limit))