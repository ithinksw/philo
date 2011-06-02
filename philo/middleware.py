from django.conf import settings
from django.contrib.sites.models import Site
from django.http import Http404

from philo.models import Node, View
from philo.utils.lazycompat import SimpleLazyObject


def get_node(path):
	"""Returns a :class:`Node` instance at ``path`` (relative to the current site) or ``None``."""
	try:
		current_site = Site.objects.get_current()
	except Site.DoesNotExist:
		current_site = None
	
	trailing_slash = False
	if path[-1] == '/':
		trailing_slash = True
	
	try:
		node, subpath = Node.objects.get_with_path(path, root=getattr(current_site, 'root_node', None), absolute_result=False)
	except Node.DoesNotExist:
		return None
	
	if subpath is None:
		subpath = ""
	subpath = "/" + subpath
	
	if trailing_slash and subpath[-1] != "/":
		subpath += "/"
	
	node._path = path
	node._subpath = subpath
	
	return node


class RequestNodeMiddleware(object):
	"""Adds a ``node`` attribute, representing the currently-viewed node, to every incoming :class:`HttpRequest` object. This is required by :func:`philo.views.node_view`."""
	def process_view(self, request, view_func, view_args, view_kwargs):
		try:
			path = view_kwargs['path']
		except KeyError:
			request.node = None
		else:
			request.node = SimpleLazyObject(lambda: get_node(path))
	
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