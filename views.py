from django.http import Http404, HttpResponse
from django.template import RequestContext
from django.contrib.sites.models import Site
from models import Node


def node_view(request, path=None, **kwargs):
	node = None
	if path is None:
		path = '/'
	try:
		current_site = Site.objects.get_current()
		if current_site:
			node = Node.objects.get_with_path(path, root=current_site.root_node)
	except Node.DoesNotExist:
		raise Http404
	if not node:
		raise Http404
	return node.instance.render_to_response(request, path=path)
