from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic
from django.contrib.sites.models import Site
from django.http import HttpResponse, HttpResponseServerError, HttpResponseRedirect
from django.core.servers.basehttp import FileWrapper
from philo.models.base import TreeEntity, Entity, QuerySetMapper
from philo.utils import ContentTypeSubclassLimiter
from philo.validators import RedirectValidator


_view_content_type_limiter = ContentTypeSubclassLimiter(None)


class Node(TreeEntity):
	view_content_type = models.ForeignKey(ContentType, related_name='node_view_set', limit_choices_to=_view_content_type_limiter)
	view_object_id = models.PositiveIntegerField()
	view = generic.GenericForeignKey('view_content_type', 'view_object_id')
	
	@property
	def accepts_subpath(self):
		return self.view.accepts_subpath
	
	def render_to_response(self, request, path=None, subpath=None, extra_context=None):
		return self.view.render_to_response(self, request, path, subpath, extra_context)
	
	class Meta:
		app_label = 'philo'


# the following line enables the selection of a node as the root for a given django.contrib.sites Site object
models.ForeignKey(Node, related_name='sites', null=True, blank=True).contribute_to_class(Site, 'root_node')


class View(Entity):
	nodes = generic.GenericRelation(Node, content_type_field='view_content_type', object_id_field='view_object_id')
	
	accepts_subpath = False
	
	def attributes_with_node(self, node):
		return QuerySetMapper(self.attribute_set, passthrough=node.attributes)
	
	def relationships_with_node(self, node):
		return QuerySetMapper(self.relationship_set, passthrough=node.relationships)
	
	def render_to_response(self, node, request, path=None, subpath=None, extra_context=None):
		raise NotImplementedError('View subclasses must implement render_to_response.')
	
	class Meta:
		abstract = True
		app_label = 'philo'


_view_content_type_limiter.cls = View


class MultiView(View):
	accepts_subpath = True
	
	urlpatterns = []
	
	def render_to_response(self, node, request, path=None, subpath=None, extra_context=None):
		if not subpath:
			subpath = ""
		subpath = "/" + subpath
		from django.core.urlresolvers import resolve
		view, args, kwargs = resolve(subpath, urlconf=self)
		return view(request, *args, **kwargs)
	
	class Meta:
		abstract = True
		app_label = 'philo'


class Redirect(View):
	STATUS_CODES = (
		(302, 'Temporary'),
		(301, 'Permanent'),
	)
	target = models.CharField(max_length=200, validators=[RedirectValidator()])
	status_code = models.IntegerField(choices=STATUS_CODES, default=302, verbose_name='redirect type')
	
	def render_to_response(self, node, request, path=None, subpath=None, extra_context=None):
		response = HttpResponseRedirect(self.target)
		response.status_code = self.status_code
		return response
	
	class Meta:
		app_label = 'philo'


class File(View):
	""" For storing arbitrary files """
	
	mimetype = models.CharField(max_length=255)
	file = models.FileField(upload_to='philo/files/%Y/%m/%d')
	
	def render_to_response(self, node, request, path=None, subpath=None, extra_context=None):
		wrapper = FileWrapper(self.file)
		response = HttpResponse(wrapper, content_type=self.mimetype)
		response['Content-Length'] = self.file.size
		return response
	
	class Meta:
		app_label = 'philo'