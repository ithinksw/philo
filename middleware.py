from django.conf import settings
from django.contrib.sites.models import Site
from django.http import Http404
from philo.models import Node, View


class LazyNode(object):
	def __get__(self, request, obj_type=None):
		if not hasattr(request, '_cached_node_path'):
			return None
		
		if not hasattr(request, '_found_node'):
			try:
				current_site = Site.objects.get_current()
			except Site.DoesNotExist:
				current_site = None
			
			path = request._cached_node_path
			trailing_slash = False
			if path[-1] == '/':
				trailing_slash = True
			
			try:
				node, subpath = Node.objects.get_with_path(path, root=getattr(current_site, 'root_node', None), absolute_result=False)
			except Node.DoesNotExist:
				node = None
			
			if node:
				if subpath is None:
					subpath = ""
				subpath = "/" + subpath
				
				if trailing_slash and subpath[-1] != "/":
					subpath += "/"
				
				node.subpath = subpath
			
			request._found_node = node
		
		return request._found_node


class RequestNodeMiddleware(object):
	"""Middleware to process the request's path and attach the closest ancestor node."""
	def process_request(self, request):
		request.__class__.node = LazyNode()
	
	def process_view(self, request, view_func, view_args, view_kwargs):
		request._cached_node_path = view_kwargs.get('path', '/')
	
	def process_exception(self, request, exception):
		if settings.DEBUG or not hasattr(request, 'node') or not request.node:
			return
		
		if isinstance(exception, Http404):
			error_view = request.node.attributes.get('Http404', None)
		else:
			error_view = request.node.attributes.get('Http500', None)
		
		if error_view is None or not isinstance(error_view, View):
			# Should this be duck-typing? Perhaps even no testing?
			return
		
		extra_context = {'exception': exception}
		return error_view.render_to_response(request, extra_context)