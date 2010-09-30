from django.contrib.sites.models import Site
from django.conf import settings
from django.http import Http404, HttpResponse
from django.template import RequestContext
from django.views.decorators.vary import vary_on_headers
from philo.models import Node


@vary_on_headers('Accept')
def node_view(request, path=None, **kwargs):
	node = None
	subpath = None
	if path is None:
		path = '/'
	current_site = Site.objects.get_current()
	try:
		node, subpath = Node.objects.get_with_path(path, root=current_site.root_node, absolute_result=False)
	except Node.DoesNotExist:
		raise Http404
	
	if not node:
		raise Http404
	
	try:
		if subpath and not node.accepts_subpath:
			raise Http404
		return node.render_to_response(request, path=path, subpath=subpath)
	except Http404, e:
		if settings.DEBUG:
			raise
		
		try:
			Http404View = node.relationships['Http404']
		except KeyError:
			Http404View = None
		
		if not Http404View:
			raise e
		
		extra_context = {'exception': e}
		
		return Http404View.render_to_response(node, request, path, subpath, extra_context)
	except Exception, e:
		if settings.DEBUG:
			raise
		
		try:
			Http500View = node.relationships['Http500']
			
			if not Http500View:
				raise e
			
			extra_context = {'exception': e}
			
			return Http500View.render_to_response(node, request, path, subpath, extra_context)
		except:
			raise e