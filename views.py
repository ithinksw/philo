from django.http import Http404, HttpResponse
from django.template import RequestContext
from django.contrib.sites.models import Site
from models import Page

def page_view(request, path=None, **kwargs):
	page = None
	if path is None:
		path = '/'
	try:
		current_site = Site.objects.get_current()
		if current_site:
			page = Page.objects.get_with_path(path, root=current_site.root_page)
	except Page.DoesNotExist:
		raise Http404
	if not page:
		raise Http404
	return HttpResponse(page.template.django_template.render(RequestContext(request, {'page': page})), mimetype=page.template.mimetype)
