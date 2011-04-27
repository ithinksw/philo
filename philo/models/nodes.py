from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic
from django.contrib.sites.models import Site, RequestSite
from django.http import HttpResponse, HttpResponseServerError, HttpResponseRedirect, Http404
from django.core.exceptions import ValidationError
from django.core.servers.basehttp import FileWrapper
from django.core.urlresolvers import resolve, clear_url_caches, reverse, NoReverseMatch
from django.template import add_to_builtins as register_templatetags
from django.utils.encoding import smart_str
from inspect import getargspec
from philo.exceptions import MIDDLEWARE_NOT_CONFIGURED
from philo.models.base import TreeEntity, Entity, QuerySetMapper, register_value_model
from philo.models.fields import JSONField
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
	
	def handles_subpath(self, subpath):
		return self.view.handles_subpath(subpath)
	
	def render_to_response(self, request, extra_context=None):
		return self.view.render_to_response(request, extra_context)
	
	def get_absolute_url(self, request=None, with_domain=False, secure=False):
		return self.construct_url(request=request, with_domain=with_domain, secure=secure)
	
	def construct_url(self, subpath="/", request=None, with_domain=False, secure=False):
		"""
		This method will construct a URL based on the Node's location.
		If a request is passed in, that will be used as a backup in case
		the Site lookup fails. The Site lookup takes precedence because
		it's what's used to find the root node. This will raise:
		- NoReverseMatch if philo-root is not reverseable
		- Site.DoesNotExist if a domain is requested but not buildable.
		- AncestorDoesNotExist if the root node of the site isn't an
		  ancestor of this instance.
		"""
		# Try reversing philo-root first, since we can't do anything if that fails.
		root_url = reverse('philo-root')
		
		try:
			current_site = Site.objects.get_current()
		except Site.DoesNotExist:
			if request is not None:
				current_site = RequestSite(request)
			elif with_domain:
				# If they want a domain and we can't figure one out,
				# best to reraise the error to let them know.
				raise
			else:
				current_site = None
		
		root = getattr(current_site, 'root_node', None)
		path = self.get_path(root=root)
		
		if current_site and with_domain:
			domain = "http%s://%s" % (secure and "s" or "", current_site.domain)
		else:
			domain = ""
		
		if not path or subpath == "/":
			subpath = subpath[1:]
		
		return '%s%s%s%s' % (domain, root_url, path, subpath)
	
	class Meta:
		app_label = 'philo'


# the following line enables the selection of a node as the root for a given django.contrib.sites Site object
models.ForeignKey(Node, related_name='sites', null=True, blank=True).contribute_to_class(Site, 'root_node')


class View(Entity):
	nodes = generic.GenericRelation(Node, content_type_field='view_content_type', object_id_field='view_object_id')
	
	accepts_subpath = False
	
	def handles_subpath(self, subpath):
		if not self.accepts_subpath and subpath != "/":
			return False
		return True
	
	def reverse(self, view_name=None, args=None, kwargs=None, node=None, obj=None):
		"""Shortcut method to handle the common pattern of getting the
		absolute url for a view's subpaths."""
		if not self.accepts_subpath:
			raise ViewDoesNotProvideSubpaths
		
		if obj is not None:
			# Perhaps just override instead of combining?
			obj_view_name, obj_args, obj_kwargs = self.get_reverse_params(obj)
			if view_name is None:
				view_name = obj_view_name
			args = list(obj_args) + list(args or [])
			obj_kwargs.update(kwargs or {})
			kwargs = obj_kwargs
		
		try:
			subpath = reverse(view_name, urlconf=self, args=args or [], kwargs=kwargs or {})
		except NoReverseMatch, e:
			raise ViewCanNotProvideSubpath(e.message)
		
		if node is not None:
			return node.construct_url(subpath)
		return subpath
	
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
		raise NotImplementedError('View subclasses must implement actually_render_to_response.')
	
	class Meta:
		abstract = True


_view_content_type_limiter.cls = View


class MultiView(View):
	accepts_subpath = True
	
	@property
	def urlpatterns(self):
		raise NotImplementedError("MultiView subclasses must implement urlpatterns.")
	
	def handles_subpath(self, subpath):
		if not super(MultiView, self).handles_subpath(subpath):
			return False
		try:
			resolve(subpath, urlconf=self)
		except Http404:
			return False
		return True
	
	def actually_render_to_response(self, request, extra_context=None):
		clear_url_caches()
		subpath = request.node.subpath
		view, args, kwargs = resolve(subpath, urlconf=self)
		view_args = getargspec(view)
		if extra_context is not None and ('extra_context' in view_args[0] or view_args[2] is not None):
			if 'extra_context' in kwargs:
				extra_context.update(kwargs['extra_context'])
			kwargs['extra_context'] = extra_context
		return view(request, *args, **kwargs)
	
	def get_context(self):
		"""Hook for providing instance-specific context - such as the value of a Field - to all views."""
		return {}
	
	def basic_view(self, field_name):
		"""
		Given the name of a field on ``self``, accesses the value of
		that field and treats it as a ``View`` instance. Creates a
		basic context based on self.get_context() and any extra_context
		that was passed in, then calls the ``View`` instance's
		render_to_response() method. This method is meant to be called
		to return a view function appropriate for urlpatterns.
		"""
		field = self._meta.get_field(field_name)
		view = getattr(self, field.name, None)
		
		def inner(request, extra_context=None, **kwargs):
			if not view:
				raise Http404
			context = self.get_context()
			context.update(extra_context or {})
			return view.render_to_response(request, extra_context=context)
		
		return inner
	
	class Meta:
		abstract = True


class TargetURLModel(models.Model):
	target_node = models.ForeignKey(Node, blank=True, null=True, related_name="%(app_label)s_%(class)s_related")
	url_or_subpath = models.CharField(max_length=200, validators=[RedirectValidator()], blank=True, help_text="Point to this url or, if a node is defined and accepts subpaths, this subpath of the node.")
	reversing_parameters = JSONField(blank=True, help_text="If reversing parameters are defined, url_or_subpath will instead be interpreted as the view name to be reversed.")
	
	def clean(self):
		if not self.target_node and not self.url_or_subpath:
			raise ValidationError("Either a target node or a url must be defined.")
		
		if self.reversing_parameters and not (self.url_or_subpath or self.target_node):
			raise ValidationError("Reversing parameters require either a view name or a target node.")
		
		try:
			self.get_target_url()
		except (NoReverseMatch, ViewCanNotProvideSubpath), e:
			raise ValidationError(e.message)
		
		super(TargetURLModel, self).clean()
	
	def get_reverse_params(self):
		params = self.reversing_parameters
		args = kwargs = None
		if isinstance(params, list):
			args = params
		elif isinstance(params, dict):
			# Convert unicode keys to strings for Python < 2.6.5. Compare
			# http://stackoverflow.com/questions/4598604/how-to-pass-unicode-keywords-to-kwargs
			kwargs = dict([(smart_str(k, 'ascii'), v) for k, v in params.items()])
		return self.url_or_subpath, args, kwargs
	
	def get_target_url(self):
		node = self.target_node
		if node is not None and node.accepts_subpath and self.url_or_subpath:
			if self.reversing_parameters is not None:
				view_name, args, kwargs = self.get_reverse_params()
				subpath = node.view.reverse(view_name, args=args, kwargs=kwargs)
			else:
				subpath = self.url_or_subpath
				if subpath[0] != '/':
					subpath = '/' + subpath
			return node.construct_url(subpath)
		elif node is not None:
			return node.get_absolute_url()
		else:
			if self.reversing_parameters is not None:
				view_name, args, kwargs = self.get_reverse_params()
				return reverse(view_name, args=args, kwargs=kwargs)
			return self.url_or_subpath
	target_url = property(get_target_url)
	
	class Meta:
		abstract = True


class Redirect(TargetURLModel, View):
	STATUS_CODES = (
		(302, 'Temporary'),
		(301, 'Permanent'),
	)
	status_code = models.IntegerField(choices=STATUS_CODES, default=302, verbose_name='redirect type')
	
	def actually_render_to_response(self, request, extra_context=None):
		response = HttpResponseRedirect(self.target_url)
		response.status_code = self.status_code
		return response
	
	class Meta:
		app_label = 'philo'


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