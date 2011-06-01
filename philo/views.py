from django.conf import settings
from django.core.urlresolvers import resolve
from django.http import Http404, HttpResponseRedirect
from django.views.decorators.vary import vary_on_headers

from philo.exceptions import MIDDLEWARE_NOT_CONFIGURED


@vary_on_headers('Accept')
def node_view(request, path=None, **kwargs):
	"""
	:func:`node_view` handles incoming requests by checking to make sure that:
	
	- the request has an attached :class:`.Node`.
	- the attached :class:`~philo.models.nodes.Node` handles any remaining path beyond its location.
	
	If these conditions are not met, then :func:`node_view` will either raise :exc:`Http404` or, if it seems like the address was mistyped (for example missing a trailing slash), return an :class:`HttpResponseRedirect` to the correct address.
	
	Otherwise, :func:`node_view` will call the :class:`.Node`'s :meth:`~.Node.render_to_response` method, passing ``kwargs`` in as the ``extra_context``.
	
	"""
	if "philo.middleware.RequestNodeMiddleware" not in settings.MIDDLEWARE_CLASSES:
		raise MIDDLEWARE_NOT_CONFIGURED
	
	if not request.node:
		if settings.APPEND_SLASH and request.path != "/":
			path = request.path
			
			if path[-1] == "/":
				path = path[:-1]
			else:
				path += "/"
			
			view, args, kwargs = resolve(path)
			if view != node_view:
				return HttpResponseRedirect(path)
		raise Http404
	
	node = request.node
	subpath = request.node._subpath
	
	# Explicitly disallow trailing slashes if we are otherwise at a node's url.
	if node._path != "/" and node._path[-1] == "/" and subpath == "/":
		return HttpResponseRedirect(node.get_absolute_url())
	
	if not node.handles_subpath(subpath):
		# If the subpath isn't handled, check settings.APPEND_SLASH. If
		# it's True, try to correct the subpath.
		if not settings.APPEND_SLASH:
			raise Http404
		
		if subpath[-1] == "/":
			subpath = subpath[:-1]
		else:
			subpath += "/"
		
		redirect_url = node.construct_url(subpath)
		
		if node.handles_subpath(subpath):
			return HttpResponseRedirect(redirect_url)
		
		# Perhaps there is a non-philo view at this address. Can we
		# resolve *something* there besides node_view? If not,
		# raise a 404.
		view, args, kwargs = resolve(redirect_url)
		
		if view == node_view:
			raise Http404
		else:
			return HttpResponseRedirect(redirect_url)
	
	return node.render_to_response(request, kwargs)