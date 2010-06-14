from django.http import Http404, HttpResponse
from django.template import RequestContext
from django.contrib.sites.models import Site
from philo.models import Node


def node_view(request, path=None, **kwargs):
	node = None
	subpath = None
	if path is None:
		path = '/'
	try:
		current_site = Site.objects.get_current()
		if current_site:
			node, subpath = Node.objects.get_with_path(path, root=current_site.root_node, absolute_result=False)
	except Node.DoesNotExist:
		raise Http404
	if not node:
		raise Http404
	if subpath and not node.instance.accepts_subpath:
		raise Http404
	return node.instance.render_to_response(request, path=path, subpath=subpath)
