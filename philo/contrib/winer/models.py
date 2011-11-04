from django.conf import settings
from django.conf.urls.defaults import url, patterns, include
from django.contrib.sites.models import Site, RequestSite
from django.contrib.syndication.views import add_domain
from django.db import models
from django.http import HttpResponse
from django.template import RequestContext, Template as DjangoTemplate
from django.utils import feedgenerator, tzinfo
from django.utils.encoding import smart_unicode, force_unicode
from django.utils.html import escape

from philo.contrib.winer.exceptions import HttpNotAcceptable
from philo.contrib.winer.feeds import registry, DEFAULT_FEED
from philo.contrib.winer.middleware import http_not_acceptable
from philo.models import Page, Template, MultiView

try:
	import mimeparse
except:
	mimeparse = None


class FeedView(MultiView):
	"""
	:class:`FeedView` is an abstract model which handles a number of pages and related feeds for a single object such as a blog or newsletter. In addition to all other methods and attributes, :class:`FeedView` supports the same generic API as `django.contrib.syndication.views.Feed <http://docs.djangoproject.com/en/dev/ref/contrib/syndication/#django.contrib.syndication.django.contrib.syndication.views.Feed>`_.
	
	"""
	#: The type of feed which should be served by the :class:`FeedView`.
	feed_type = models.CharField(max_length=50, choices=registry.choices, default=registry.get_slug(DEFAULT_FEED))
	#: The suffix which will be appended to a page URL for a :attr:`feed_type` feed of its items. Default: "feed". Note that RSS and Atom feeds will always be available at ``<page_url>/rss`` and ``<page_url>/atom`` regardless of the value of this setting.
	#:
	#: .. seealso:: :meth:`get_feed_type`, :meth:`feed_patterns`
	feed_suffix = models.CharField(max_length=255, blank=False, default="feed")
	#: A :class:`BooleanField` - whether or not feeds are enabled.
	feeds_enabled = models.BooleanField(default=True)
	#: A :class:`PositiveIntegerField` - the maximum number of items to return for this feed. All items will be returned if this field is blank. Default: 15.
	feed_length = models.PositiveIntegerField(blank=True, null=True, default=15, help_text="The maximum number of items to return for this feed. All items will be returned if this field is blank.")
	
	#: A :class:`ForeignKey` to a :class:`.Template` which will be used to render the title of each item in the feed if provided.
	item_title_template = models.ForeignKey(Template, blank=True, null=True, related_name="%(app_label)s_%(class)s_title_related")
	#: A :class:`ForeignKey` to a :class:`.Template` which will be used to render the description of each item in the feed if provided.
	item_description_template = models.ForeignKey(Template, blank=True, null=True, related_name="%(app_label)s_%(class)s_description_related")
	
	#: An attribute holding the name of the context variable to be populated with the items managed by the :class:`FeedView`. Default: "items"
	item_context_var = 'items'
	#: An attribute holding the name of the attribute on a subclass of :class:`FeedView` which will contain the main object of a feed (such as a :class:`~philo.contrib.penfield.models.Blog`.) Default: "object"
	#:
	#: Example::
	#:
	#:     class BlogView(FeedView):
	#:         blog = models.ForeignKey(Blog)
	#:         
	#:         object_attr = 'blog'
	#:         item_context_var = 'entries'
	object_attr = 'object'
	
	#: An attribute holding a description of the feeds served by the :class:`FeedView`. This is a required part of the :class:`django.contrib.syndication.view.Feed` API.
	description = ""
	
	def feed_patterns(self, base, get_items_attr, page_attr, reverse_name):
		"""
		Given the name to be used to reverse this view and the names of the attributes for the function that fetches the objects, returns patterns suitable for inclusion in urlpatterns. In addition to ``base`` (which will serve the page at ``page_attr``) and ``base`` + :attr:`feed_suffix` (which will serve a :attr:`feed_type` feed), patterns will be provided for each registered feed type as ``base`` + ``slug``.
		
		:param base: The base of the returned patterns - that is, the subpath pattern which will reference the page for the items. The :attr:`feed_suffix` will be appended to this subpath.
		:param get_items_attr: A callable or the name of a callable on the :class:`FeedView` which will return an (``items``, ``extra_context``) tuple. This will be passed directly to :meth:`feed_view` and :meth:`page_view`.
		:param page_attr: A :class:`.Page` instance or the name of an attribute on the :class:`FeedView` which contains a :class:`.Page` instance. This will be passed directly to :meth:`page_view` and will be rendered with the items from ``get_items_attr``.
		:param reverse_name: The string which is considered the "name" of the view function returned by :meth:`page_view` for the given parameters.
		:returns: Patterns suitable for use in urlpatterns.
		
		Example::
		
			class BlogView(FeedView):
			    blog = models.ForeignKey(Blog)
			    entry_archive_page = models.ForeignKey(Page)
			    
			    @property
			    def urlpatterns(self):
			        urlpatterns = self.feed_patterns(r'^', 'get_all_entries', 'index_page', 'index')
			        urlpatterns += self.feed_patterns(r'^(?P<year>\d{4})/(?P<month>\d{2})/(?P<day>\d{2})', 'get_entries_by_ymd', 'entry_archive_page', 'entries_by_day')
			        return urlpatterns
			    
			    def get_entries_by_ymd(request, year, month, day, extra_context=None):
			        entries = Blog.entries.all()
			        # filter entries based on the year, month, and day.
			        return entries, extra_context
		
		.. seealso:: :meth:`get_feed_type`
		
		"""
		feed_patterns = ()
		if self.feeds_enabled:
			suffixes = [(self.feed_suffix, None)] + [(slug, slug) for slug in registry]
			for suffix, feed_type in suffixes:
				feed_view = http_not_acceptable(self.feed_view(get_items_attr, reverse_name, feed_type))
				feed_pattern = r'%s%s%s$' % (base, "/" if base and base[-1] != "^" else "", suffix)
				feed_patterns += (url(feed_pattern, feed_view, name="%s_%s" % (reverse_name, suffix)),)
		feed_patterns += (url(r"%s$" % base, self.page_view(get_items_attr, page_attr), name=reverse_name),)
		return patterns('', *feed_patterns)
	
	def get_object(self, request, **kwargs):
		"""By default, returns the object stored in the attribute named by :attr:`object_attr`. This can be overridden for subclasses that publish different data for different URL parameters. It is part of the :class:`django.contrib.syndication.views.Feed` API."""
		return getattr(self, self.object_attr)
	
	def feed_view(self, get_items_attr, reverse_name, feed_type=None):
		"""
		Returns a view function that renders a list of items as a feed.
		
		:param get_items_attr: A callable or the name of a callable on the :class:`FeedView` that will return a (items, extra_context) tuple when called with the object for the feed and view arguments.
		:param reverse_name: The name which can be used reverse the page for this feed using the :class:`FeedView` as the urlconf.
		:param feed_type: The slug used to render the feed class which will be used by the returned view function.
		
		:returns: A view function that renders a list of items as a feed.
		
		"""
		get_items = get_items_attr if callable(get_items_attr) else getattr(self, get_items_attr)
		
		def inner(request, extra_context=None, *args, **kwargs):
			obj = self.get_object(request, *args, **kwargs)
			feed = self.get_feed(obj, request, reverse_name, feed_type, *args, **kwargs)
			items, xxx = get_items(obj, request, extra_context=extra_context, *args, **kwargs)
			self.populate_feed(feed, items, request)
			
			response = HttpResponse(mimetype=feed.mime_type)
			feed.write(response, 'utf-8')
			return response
		
		return inner
	
	def page_view(self, get_items_attr, page_attr):
		"""
		:param get_items_attr: A callable or the name of a callable on the :class:`FeedView` that will return a (items, extra_context) tuple when called with view arguments.
		:param page_attr: A :class:`.Page` instance or the name of an attribute on the :class:`FeedView` which contains a :class:`.Page` instance. This will be rendered with the items from ``get_items_attr``.
		
		:returns: A view function that renders a list of items as an :class:`HttpResponse`.
		
		"""
		get_items = get_items_attr if callable(get_items_attr) else getattr(self, get_items_attr)
		
		def inner(request, extra_context=None, *args, **kwargs):
			obj = self.get_object(request, *args, **kwargs)
			items, extra_context = get_items(obj, request, extra_context=extra_context, *args, **kwargs)
			items, item_context = self.process_page_items(request, items)
			
			context = self.get_context()
			context.update(extra_context or {})
			context.update(item_context or {})
			
			page = page_attr if isinstance(page_attr, Page) else getattr(self, page_attr)
			return page.render_to_response(request, extra_context=context)
		return inner
	
	def process_page_items(self, request, items):
		"""
		Hook for handling any extra processing of ``items`` based on an :class:`HttpRequest`, such as pagination or searching. This method is expected to return a list of items and a dictionary to be added to the page context.
		
		"""
		item_context = {
			self.item_context_var: items
		}
		return items, item_context
	
	def get_feed_type(self, request, feed_type=None):
		"""
		If ``feed_type`` is not ``None``, returns the corresponding class from the registry or raises :exc:`.HttpNotAcceptable`.
		
		Otherwise, intelligently chooses a feed type for a given request. Tries to return :attr:`feed_type`, but if the Accept header does not include that mimetype, tries to return the best match from the feed types that are offered by the :class:`FeedView`. If none of the offered feed types are accepted by the :class:`HttpRequest`, raises :exc:`.HttpNotAcceptable`.
		
		If `mimeparse <http://code.google.com/p/mimeparse/>`_ is installed, it will be used to select the best matching accepted format; otherwise, the first available format that is accepted will be selected.
		
		"""
		if feed_type is not None:
			feed_type = registry[feed_type]
			loose = False
		else:
			feed_type = registry.get(self.feed_type, DEFAULT_FEED)
			loose = True
		mt = feed_type.mime_type
		accept = request.META.get('HTTP_ACCEPT')
		if accept and mt not in accept and "*/*" not in accept and "%s/*" % mt.split("/")[0] not in accept:
			# Wups! They aren't accepting the chosen format.
			feed_type = None
			if loose:
				# Is there another format we can use?
				accepted_mts = dict([(obj.mime_type, obj) for obj in registry.values()])
				if mimeparse:
					mt = mimeparse.best_match(accepted_mts.keys(), accept)
					if mt:
						feed_type = accepted_mts[mt]
				else:
					for mt in accepted_mts:
						if mt in accept or "%s/*" % mt.split("/")[0] in accept:
							feed_type = accepted_mts[mt]
							break
			if not feed_type:
				raise HttpNotAcceptable
		return feed_type
	
	def get_feed(self, obj, request, reverse_name, feed_type=None, *args, **kwargs):
		"""
		Returns an unpopulated :class:`django.utils.feedgenerator.DefaultFeed` object for this object.
		
		:param obj: The object for which the feed should be generated.
		:param request: The current request.
		:param reverse_name: The name which can be used to reverse the URL of the page corresponding to this feed.
		:param feed_type: The slug used to register the feed class that will be instantiated and returned.
		
		:returns: An instance of the feed class registered as ``feed_type``, falling back to :attr:`feed_type` if ``feed_type`` is ``None``.
		
		"""
		try:
			current_site = Site.objects.get_current()
		except Site.DoesNotExist:
			current_site = RequestSite(request)
		
		feed_type = self.get_feed_type(request, feed_type)
		node = request.node
		link = node.construct_url(self.reverse(reverse_name, args=args, kwargs=kwargs), with_domain=True, request=request, secure=request.is_secure())
		
		feed = feed_type(
			title = self.__get_dynamic_attr('title', obj),
			subtitle = self.__get_dynamic_attr('subtitle', obj),
			link = link,
			description = self.__get_dynamic_attr('description', obj),
			language = settings.LANGUAGE_CODE.decode(),
			feed_url = add_domain(
				current_site.domain,
				self.__get_dynamic_attr('feed_url', obj) or node.construct_url(self.reverse("%s_%s" % (reverse_name, registry.get_slug(feed_type)), args=args, kwargs=kwargs), with_domain=True, request=request, secure=request.is_secure()),
				request.is_secure()
			),
			author_name = self.__get_dynamic_attr('author_name', obj),
			author_link = self.__get_dynamic_attr('author_link', obj),
			author_email = self.__get_dynamic_attr('author_email', obj),
			categories = self.__get_dynamic_attr('categories', obj),
			feed_copyright = self.__get_dynamic_attr('feed_copyright', obj),
			feed_guid = self.__get_dynamic_attr('feed_guid', obj),
			ttl = self.__get_dynamic_attr('ttl', obj),
			**self.feed_extra_kwargs(obj)
		)
		return feed
	
	def populate_feed(self, feed, items, request):
		"""Populates a :class:`django.utils.feedgenerator.DefaultFeed` instance as is returned by :meth:`get_feed` with the passed-in ``items``."""
		if self.item_title_template:
			title_template = DjangoTemplate(self.item_title_template.code)
		else:
			title_template = None
		if self.item_description_template:
			description_template = DjangoTemplate(self.item_description_template.code)
		else:
			description_template = None
		
		node = request.node
		try:
			current_site = Site.objects.get_current()
		except Site.DoesNotExist:
			current_site = RequestSite(request)
		
		if self.feed_length is not None:
			items = items[:self.feed_length]
		
		for item in items:
			if title_template is not None:
				title = title_template.render(RequestContext(request, {'obj': item}))
			else:
				title = self.__get_dynamic_attr('item_title', item)
			if description_template is not None:
				description = description_template.render(RequestContext(request, {'obj': item}))
			else:
				description = self.__get_dynamic_attr('item_description', item)
			
			link = node.construct_url(self.reverse(obj=item), with_domain=True, request=request, secure=request.is_secure())
			
			enc = None
			enc_url = self.__get_dynamic_attr('item_enclosure_url', item)
			if enc_url:
				enc = feedgenerator.Enclosure(
					url = smart_unicode(add_domain(
							current_site.domain,
							enc_url,
							request.is_secure()
					)),
					length = smart_unicode(self.__get_dynamic_attr('item_enclosure_length', item)),
					mime_type = smart_unicode(self.__get_dynamic_attr('item_enclosure_mime_type', item))
				)
			author_name = self.__get_dynamic_attr('item_author_name', item)
			if author_name is not None:
				author_email = self.__get_dynamic_attr('item_author_email', item)
				author_link = self.__get_dynamic_attr('item_author_link', item)
			else:
				author_email = author_link = None
			
			pubdate = self.__get_dynamic_attr('item_pubdate', item)
			if pubdate and not pubdate.tzinfo:
				ltz = tzinfo.LocalTimezone(pubdate)
				pubdate = pubdate.replace(tzinfo=ltz)
			
			feed.add_item(
				title = title,
				link = link,
				description = description,
				unique_id = self.__get_dynamic_attr('item_guid', item, link),
				enclosure = enc,
				pubdate = pubdate,
				author_name = author_name,
				author_email = author_email,
				author_link = author_link,
				categories = self.__get_dynamic_attr('item_categories', item),
				item_copyright = self.__get_dynamic_attr('item_copyright', item),
				**self.item_extra_kwargs(item)
			)
	
	def __get_dynamic_attr(self, attname, obj, default=None):
		try:
			attr = getattr(self, attname)
		except AttributeError:
			return default
		if callable(attr):
			# Check func_code.co_argcount rather than try/excepting the
			# function and catching the TypeError, because something inside
			# the function may raise the TypeError. This technique is more
			# accurate.
			if hasattr(attr, 'func_code'):
				argcount = attr.func_code.co_argcount
			else:
				argcount = attr.__call__.func_code.co_argcount
			if argcount == 2: # one argument is 'self'
				return attr(obj)
			else:
				return attr()
		return attr
	
	def feed_extra_kwargs(self, obj):
		"""Returns an extra keyword arguments dictionary that is used when initializing the feed generator."""
		return {}
	
	def item_extra_kwargs(self, item):
		"""Returns an extra keyword arguments dictionary that is used with the `add_item` call of the feed generator."""
		return {}
	
	def item_title(self, item):
		return escape(force_unicode(item))
	
	def item_description(self, item):
		return force_unicode(item)
	
	class Meta:
		abstract=True