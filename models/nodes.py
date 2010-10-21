from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic
from django.contrib.sites.models import Site
from django.http import HttpResponse, HttpResponseServerError, HttpResponseRedirect
from django.core.exceptions import ViewDoesNotExist
from django.core.servers.basehttp import FileWrapper
from django.core.urlresolvers import resolve, clear_url_caches, reverse, NoReverseMatch
from django.template import add_to_builtins as register_templatetags
from inspect import getargspec
from philo.exceptions import MIDDLEWARE_NOT_CONFIGURED
from philo.models.base import TreeEntity, Entity, QuerySetMapper, register_value_model
from philo.utils import ContentTypeSubclassLimiter
from philo.validators import RedirectValidator
from philo.exceptions import ViewCanNotProvideSubpath, ViewDoesNotProvideSubpaths, AncestorDoesNotExist
from philo.signals import view_about_to_render, view_finished_rendering


_view_content_type_limiter = ContentTypeSubclassLimiter(None)


class Node(TreeEntity):
	view_content_type = models.ForeignKey(ContentType, related_name='node_view_set', limit_choices_to=_view_content_type_limiter)
	view_object_id = models.PositiveIntegerField()
	view = generic.GenericForeignKey('view_content_type', 'view_object_id')
	
	@property
	def accepts_subpath(self):
		if self.view:
			return self.view.accepts_subpath
		return False
	
	def render_to_response(self, request, extra_context=None):
		return self.view.render_to_response(request, extra_context)
	
	def get_absolute_url(self):
		try:
			root = Site.objects.get_current().root_node
		except Site.DoesNotExist:
			root = None
		
		try:
			path = self.get_path(root=root)
			if path:
				path += '/'
			root_url = reverse('philo-root')
			return '%s%s' % (root_url, path)
		except AncestorDoesNotExist, ViewDoesNotExist:
			return None
	
	class Meta:
		app_label = 'philo'


# the following line enables the selection of a node as the root for a given django.contrib.sites Site object
models.ForeignKey(Node, related_name='sites', null=True, blank=True).contribute_to_class(Site, 'root_node')


class View(Entity):
	nodes = generic.GenericRelation(Node, content_type_field='view_content_type', object_id_field='view_object_id')
	
	accepts_subpath = False
	
	def get_subpath(self, obj):
		if not self.accepts_subpath:
			raise ViewDoesNotProvideSubpaths
		
		view_name, args, kwargs = self.get_reverse_params(obj)
		try:
			return reverse(view_name, args=args, kwargs=kwargs, urlconf=self)
		except NoReverseMatch:
			raise ViewCanNotProvideSubpath
	
	def get_reverse_params(self, obj):
		"""This method should return a view_name, args, kwargs tuple suitable for reversing a url for the given obj using self as the urlconf."""
		raise NotImplementedError("View subclasses must implement get_reverse_params to support subpaths.")
	
	def attributes_with_node(self, node):
		return QuerySetMapper(self.attribute_set, passthrough=node.attributes)
	
	def render_to_response(self, request, extra_context=None):
		if not hasattr(request, 'node'):
			raise MIDDLEWARE_NOT_CONFIGURED
		
		extra_context = extra_context or {}
		view_about_to_render.send(sender=self, request=request, extra_context=extra_context)
		response = self.actually_render_to_response(request, extra_context)
		view_finished_rendering.send(sender=self, response=response)
		return response
	
	def actually_render_to_response(self, request, extra_context=None):
		raise NotImplementedError('View subclasses must implement render_to_response.')
	
	class Meta:
		abstract = True


_view_content_type_limiter.cls = View


class MultiView(View):
	accepts_subpath = True
	
	@property
	def urlpatterns(self, obj):
		raise NotImplementedError("MultiView subclasses must implement urlpatterns.")
	
	def actually_render_to_response(self, request, extra_context=None):
		clear_url_caches()
		subpath = request.node.subpath
		if not subpath:
			subpath = ""
		subpath = "/" + subpath
		view, args, kwargs = resolve(subpath, urlconf=self)
		view_args = getargspec(view)
		if extra_context is not None and ('extra_context' in view_args[0] or view_args[2] is not None):
			if 'extra_context' in kwargs:
				extra_context.update(kwargs['extra_context'])
			kwargs['extra_context'] = extra_context
		return view(request, *args, **kwargs)
	
	class Meta:
		abstract = True


class Redirect(View):
	STATUS_CODES = (
		(302, 'Temporary'),
		(301, 'Permanent'),
	)
	target = models.CharField(max_length=200, validators=[RedirectValidator()])
	status_code = models.IntegerField(choices=STATUS_CODES, default=302, verbose_name='redirect type')
	
	def actually_render_to_response(self, request, extra_context=None):
		response = HttpResponseRedirect(self.target)
		response.status_code = self.status_code
		return response
	
	class Meta:
		app_label = 'philo'


# Why does this exist?
class File(View):
	""" For storing arbitrary files """
	
	mimetype = models.CharField(max_length=255)
	file = models.FileField(upload_to='philo/files/%Y/%m/%d')
	
	def actually_render_to_response(self, request, extra_context=None):
		wrapper = FileWrapper(self.file)
		response = HttpResponse(wrapper, content_type=self.mimetype)
		response['Content-Length'] = self.file.size
		return response
	
	class Meta:
		app_label = 'philo'
	
	def __unicode__(self):
		return self.file.name


register_templatetags('philo.templatetags.nodes')
register_value_model(Node)