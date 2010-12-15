from django.utils.feedgenerator import Atom1Feed, Rss201rev2Feed
from django.conf.urls.defaults import url, patterns
from django.contrib.sites.models import Site
from django.core.urlresolvers import reverse
from django.http import HttpResponse
from philo.utils import paginate


class FeedMultiViewMixin(object):
	"""
	This mixin provides common methods for adding feeds to multiviews. In order to use this mixin,
	the multiview must define feed_title (probably as properties that return values
	on related objects.) feed_description may also be defined; it defaults to an empty string.
	"""
	feed_suffix = 'feed'
	feeds_enabled = True
	atom_feed = Atom1Feed
	rss_feed = Rss201rev2Feed
	feed_title = None
	feed_description = None
	list_var = 'objects'
	
	def page_view(self, func, page):
		"""
		Wraps an object-fetching function and renders the results as a page.
		"""
		def inner(request, extra_context=None, **kwargs):
			objects, extra_context = func(request=request, extra_context=extra_context, **kwargs)

			context = self.get_context()
			context.update(extra_context or {})

			if 'page' in kwargs or 'page' in request.GET or (hasattr(self, 'per_page') and self.per_page):
				page_num = kwargs.get('page', request.GET.get('page', 1))
				paginator, paginated_page, objects = paginate(objects, self.per_page, page_num)
				context.update({'paginator': paginator, 'paginated_page': paginated_page, self.list_var: objects})
			else:
				context.update({self.list_var: objects})

			return page.render_to_response(request, extra_context=context)

		return inner
	
	def feed_view(self, func, reverse_name):
		"""
		Wraps an object-fetching function and renders the results as a rss or atom feed.
		"""
		def inner(request, extra_context=None, **kwargs):
			objects, extra_context = func(request=request, extra_context=extra_context, **kwargs)
	
			if 'HTTP_ACCEPT' in request.META and 'rss' in request.META['HTTP_ACCEPT'] and 'atom' not in request.META['HTTP_ACCEPT']:
				feed_type = 'rss'
			else:
				feed_type = 'atom'
			
			current_site = Site.objects.get_current()
			#Could this be done with request.path instead somehow?
			feed_kwargs = {
				'link': 'http://%s/%s/%s/' % (current_site.domain, request.node.get_absolute_url().strip('/'), reverse(reverse_name, urlconf=self, kwargs=kwargs).strip('/'))
			}
			feed = self.get_feed(feed_type, extra_context, feed_kwargs)
			
			for obj in objects:
				kwargs = {
					'link': 'http://%s/%s/%s/' % (current_site.domain, request.node.get_absolute_url().strip('/'), self.get_subpath(obj).strip('/'))
				}
				self.add_item(feed, obj, kwargs=kwargs)
	
			response = HttpResponse(mimetype=feed.mime_type)
			feed.write(response, 'utf-8')
			return response

		return inner
	
	def get_feed(self, feed_type, extra_context, kwargs=None):
		defaults = {
			'description': ''
		}
		defaults.update(kwargs or {})
		
		if feed_type == 'rss':
			return self.rss_feed(**defaults)
		
		if 'description' in defaults and defaults['description'] and 'subtitle' not in defaults:
			defaults['subtitle'] = defaults['description']
		
		return self.atom_feed(**defaults)
	
	def feed_patterns(self, object_fetcher, page, base_name):
		urlpatterns = patterns('',
			url(r'^$', self.page_view(object_fetcher, page), name=base_name)
		)
		if self.feeds_enabled:
			feed_name = '%s_feed' % base_name
			urlpatterns = patterns('',
				url(r'^%s/$' % self.feed_suffix, self.feed_view(object_fetcher, feed_name), name=feed_name),
			) + urlpatterns
		return urlpatterns
	
	def add_item(self, feed, obj, kwargs=None):
		defaults = kwargs or {}
		feed.add_item(**defaults)