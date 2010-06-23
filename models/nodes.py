from django.db import models
from django.contrib.sites.models import Site
from django.http import HttpResponse, HttpResponseServerError, HttpResponseRedirect
from django.core.servers.basehttp import FileWrapper
from philo.models.base import InheritableTreeEntity
from philo.validators import RedirectValidator


class Node(InheritableTreeEntity):
	accepts_subpath = False
	
	def render_to_response(self, request, path=None, subpath=None):
		return HttpResponseServerError()
		
	class Meta:
		unique_together = (('parent', 'slug'),)
		app_label = 'philo'


# the following line enables the selection of a node as the root for a given django.contrib.sites Site object
models.ForeignKey(Node, related_name='sites', null=True, blank=True).contribute_to_class(Site, 'root_node')


class MultiNode(Node):
	accepts_subpath = True
	
	urlpatterns = []
	
	def render_to_response(self, request, path=None, subpath=None):
		if not subpath:
			subpath = ""
		subpath = "/" + subpath
		from django.core.urlresolvers import resolve
		view, args, kwargs = resolve(subpath, urlconf=self)
		return view(request, *args, **kwargs)
	
	class Meta:
		abstract = True
		app_label = 'philo'


class Redirect(Node):
	STATUS_CODES = (
		(302, 'Temporary'),
		(301, 'Permanent'),
	)
	target = models.CharField(max_length=200,validators=[RedirectValidator()])
	status_code = models.IntegerField(choices=STATUS_CODES, default=302, verbose_name='redirect type')
	
	def render_to_response(self, request, path=None, subpath=None):
		response = HttpResponseRedirect(self.target)
		response.status_code = self.status_code
		return response
	
	class Meta:
		app_label = 'philo'


class File(Node):
	""" For storing arbitrary files """
	mimetype = models.CharField(max_length=255)
	file = models.FileField(upload_to='philo/files/%Y/%m/%d')
	
	def render_to_response(self, request, path=None, subpath=None):
		wrapper = FileWrapper(self.file)
		response = HttpResponse(wrapper, content_type=self.mimetype)
		response['Content-Length'] = self.file.size
		return response
	
	class Meta:
		app_label = 'philo'