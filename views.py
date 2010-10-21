from django.contrib.sites.models import Site
from django.conf import settings
from django.http import Http404, HttpResponse
from django.template import RequestContext
from django.views.decorators.vary import vary_on_headers
from philo.exceptions import MIDDLEWARE_NOT_CONFIGURED
from philo.models import Node


@vary_on_headers('Accept')
def node_view(request, path=None, **kwargs):
	if not hasattr(request, 'node'):
		raise MIDDLEWARE_NOT_CONFIGURED
	
	if not request.node:
		raise Http404
	
	node = request.node
	subpath = request.node.subpath
	
	try:
		if subpath and not node.accepts_subpath:
			raise Http404
		return node.render_to_response(request, kwargs)
	except Http404, e:
		if settings.DEBUG:
			raise
		
		try:
			Http404View = node.attributes['Http404']
		except KeyError:
			Http404View = None
		
		if not Http404View:
			raise e
		
		extra_context = {'exception': e}
		
		return Http404View.render_to_response(request, extra_context)
	except Exception, e:
		if settings.DEBUG:
			raise
		
		try:
			Http500View = node.attributes['Http500']
			
			if not Http500View:
				raise e
			
			extra_context = {'exception': e}
			
			return Http500View.render_to_response(request, extra_context)
		except:
			raise e