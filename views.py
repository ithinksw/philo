from django.http import Http404
from django.views.decorators.vary import vary_on_headers
from philo.exceptions import MIDDLEWARE_NOT_CONFIGURED


@vary_on_headers('Accept')
def node_view(request, path=None, **kwargs):
	if not hasattr(request, 'node'):
		raise MIDDLEWARE_NOT_CONFIGURED
	
	if not request.node:
		raise Http404
	
	node = request.node
	subpath = request.node.subpath
	
	if subpath and not node.accepts_subpath:
		raise Http404
	return node.render_to_response(request, kwargs)