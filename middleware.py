from django.contrib.sites.models import Site
from philo.models import Node


class LazyNode(object):
	def __get__(self, request, obj_type=None):
		if not hasattr(request, '_cached_node_path'):
			return None
		
		if not hasattr(request, '_found_node'):
			try:
				current_site = Site.objects.get_current()
			except Site.DoesNotExist:
				current_site = None
			
			try:
				node, subpath = Node.objects.get_with_path(request._cached_node_path, root=getattr(current_site, 'root_node', None), absolute_result=False)
			except Node.DoesNotExist:
				node = None
			
			if node:
				node.subpath = subpath
			
			request._found_node = node
		
		return request._found_node


class RequestNodeMiddleware(object):
	"""Middleware to process the request's path and attach the closest ancestor node."""
	def process_request(self, request):
		request.__class__.node = LazyNode()
	
	def process_view(self, request, view_func, view_args, view_kwargs):
		request._cached_node_path = view_kwargs.get('path', '/')