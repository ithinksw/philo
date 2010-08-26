from django.utils.feedgenerator import Atom1Feed, Rss201rev2Feed
from django.conf.urls.defaults import url, patterns
from django.core.urlresolvers import reverse
from django.http import HttpResponse


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
	feed_description = ''
	list_var = 'objects'
	
	def page_view(self, func, page):
		"""
		Wraps an object-fetching function and renders the results as a page.
		"""
		def inner(request, node=None, extra_context=None, **kwargs):
			objects, extra_context = func(request=request, node=node, extra_context=extra_context, **kwargs)

			context = self.get_context()
			context.update(extra_context or {})

			if 'page' in kwargs or 'page' in request.GET:
				page_num = kwargs.get('page', request.GET.get('page', 1))
				paginator, paginated_page, objects = paginate(objects, self.per_page, page_num)
				context.update({'paginator': paginator, 'paginated_page': paginated_page, self.list_var: objects})
			else:
				context.update({self.list_var: objects})

			return page.render_to_response(node, request, extra_context=context)

		return inner
	
	def feed_view(self, func, reverse_name):
		"""
		Wraps an object-fetching function and renders the results as a rss or atom feed.
		"""
		def inner(request, node=None, extra_context=None, **kwargs):
			objects, extra_context = func(request=request, node=node, extra_context=extra_context, **kwargs)
	
			if 'HTTP_ACCEPT' in request.META and 'rss' in request.META['HTTP_ACCEPT'] and 'atom' not in request.META['HTTP_ACCEPT']:
				feed_type = 'rss'
			else:
				feed_type = 'atom'
			
			feed = self.get_feed(feed_type, request, node, kwargs, reverse_name)
			
			for obj in objects:
				feed.add_item(obj.title, '/%s/%s/' % (node.get_absolute_url().strip('/'), self.get_subpath(obj).strip('/')), description=self.get_obj_description(obj))
	
			response = HttpResponse(mimetype=feed.mime_type)
			feed.write(response, 'utf-8')
			return response

		return inner
	
	def get_feed(self, feed_type, request, node, kwargs, reverse_name):
		title = self.feed_title
		link = '/%s/%s/' % (node.get_absolute_url().strip('/'), reverse(reverse_name, urlconf=self, kwargs=kwargs).strip('/'))
		description = self.feed_description
		if feed_type == 'rss':
			return self.rss_feed(title, link, description)
		
		return self.atom_feed(title, link, description, subtitle=description)
	
	def feed_patterns(self, object_fetcher, page, base_name):
		feed_name = '%s_feed' % base_name
		urlpatterns = patterns('',
			url(r'^%s/$' % self.feed_suffix, self.feed_view(object_fetcher, feed_name), name=feed_name),
			url(r'^$', self.page_view(object_fetcher, page), name=base_name)
		)
		return urlpatterns
	
	def get_obj_description(self, obj):
		raise NotImplementedError