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
	"""
	Adds a ``node`` attribute, representing the currently-viewed :class:`.Node`, to every incoming :class:`HttpRequest` object. This is required by :func:`philo.views.node_view`.
	
	:class:`RequestNodeMiddleware` also catches all exceptions raised while handling requests that have attached :class:`.Node`\ s if :setting:`settings.DEBUG` is ``True``. If a :exc:`django.http.Http404` error was caught, :class:`RequestNodeMiddleware` will look for an "Http404" :class:`.Attribute` on the request's :class:`.Node`; otherwise it will look for an "Http500" :class:`.Attribute`. If an appropriate :class:`.Attribute` is found, and the value of the attribute is a :class:`.View` instance, then the :class:`.View` will be rendered with the exception in the ``extra_context``, bypassing any later handling of exceptions.
	
	"""
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
			status_code = 404
		else:
			error_view = request.node.attributes.get('Http500', None)
			status_code = 500
		
		if error_view is None or not isinstance(error_view, View):
			# Should this be duck-typing? Perhaps even no testing?
			return
		
		extra_context = {'exception': exception}
		response = error_view.render_to_response(request, extra_context)
		response.status_code = status_code
		return response