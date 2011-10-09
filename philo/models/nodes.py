from inspect import getargspec
import mimetypes
from os.path import basename

from django.conf import settings
from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.models import Site, RequestSite
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.servers.basehttp import FileWrapper
from django.core.urlresolvers import resolve, clear_url_caches, reverse, NoReverseMatch
from django.db import models
from django.http import HttpResponse, HttpResponseServerError, HttpResponseRedirect, Http404
from django.utils.encoding import smart_str

from philo.exceptions import MIDDLEWARE_NOT_CONFIGURED, ViewCanNotProvideSubpath, ViewDoesNotProvideSubpaths
from philo.models.base import SlugTreeEntity, Entity, register_value_model
from philo.models.fields import JSONField
from philo.utils import ContentTypeSubclassLimiter
from philo.utils.entities import LazyPassthroughAttributeMapper
from philo.signals import view_about_to_render, view_finished_rendering


__all__ = ('Node', 'View', 'MultiView', 'Redirect', 'File')


_view_content_type_limiter = ContentTypeSubclassLimiter(None)
CACHE_PHILO_ROOT = getattr(settings, "PHILO_CACHE_PHILO_ROOT", True)


class Node(SlugTreeEntity):
	"""
	:class:`Node`\ s are the basic building blocks of a website using Philo. They define the URL hierarchy and connect each URL to a :class:`View` subclass instance which is used to generate an HttpResponse.
	
	"""
	view_content_type = models.ForeignKey(ContentType, related_name='node_view_set', limit_choices_to=_view_content_type_limiter, blank=True, null=True)
	view_object_id = models.PositiveIntegerField(blank=True, null=True)
	#: :class:`GenericForeignKey` to a non-abstract subclass of :class:`View`
	view = generic.GenericForeignKey('view_content_type', 'view_object_id')
	
	@property
	def accepts_subpath(self):
		"""A property shortcut for :attr:`self.view.accepts_subpath <View.accepts_subpath>`"""
		if self.view_object_id and self.view_content_type_id:
			return ContentType.objects.get_for_id(self.view_content_type_id).model_class().accepts_subpath
		return False
	
	def handles_subpath(self, subpath):
		if self.view_object_id and self.view_content_type_id:
			return ContentType.objects.get_for_id(self.view_content_type_id).model_class().handles_subpath(subpath)
		return False
	
	def render_to_response(self, request, extra_context=None):
		"""This is a shortcut method for :meth:`View.render_to_response`"""
		if self.view_object_id and self.view_content_type_id:
			view_model = ContentType.objects.get_for_id(self.view_content_type_id).model_class()
			self.view = view_model._default_manager.get(pk=self.view_object_id)
			return self.view.render_to_response(request, extra_context)
		raise Http404
	
	def get_absolute_url(self, request=None, with_domain=False, secure=False):
		"""
		This is essentially a shortcut for calling :meth:`construct_url` without a subpath.
		
		:returns: The absolute url of the node on the current site.
		
		"""
		return self.construct_url(request=request, with_domain=with_domain, secure=secure)
	
	def construct_url(self, subpath="/", request=None, with_domain=False, secure=False):
		"""
		This method will do its best to construct a URL based on the Node's location. If with_domain is True, that URL will include a domain and a protocol; if secure is True as well, the protocol will be https. The request will be used to construct a domain in cases where a call to :meth:`Site.objects.get_current` fails.
		
		Node urls will not contain a trailing slash unless a subpath is provided which ends with a trailing slash. Subpaths are expected to begin with a slash, as if returned by :func:`django.core.urlresolvers.reverse`.
		
		Because this method will be called frequently and will always try to reverse ``philo-root``, the results of that reversal will be cached by default. This can be disabled by setting :setting:`PHILO_CACHE_PHILO_ROOT` to ``False``.
		
		:meth:`construct_url` may raise the following exceptions:
		
		- :class:`NoReverseMatch` if "philo-root" is not reversable -- for example, if :mod:`philo.urls` is not included anywhere in your urlpatterns.
		- :class:`Site.DoesNotExist <ObjectDoesNotExist>` if with_domain is True but no :class:`Site` or :class:`RequestSite` can be built.
		- :class:`~philo.exceptions.AncestorDoesNotExist` if the root node of the site isn't an ancestor of the node constructing the URL.
		
		:param string subpath: The subpath to be constructed beyond beyond the node's URL.
		:param request: :class:`HttpRequest` instance. Will be used to construct a :class:`RequestSite` if :meth:`Site.objects.get_current` fails.
		:param with_domain: Whether the constructed URL should include a domain name and protocol.
		:param secure: Whether the protocol, if included, should be http:// or https://.
		:returns: A constructed url for accessing the given subpath of the current node instance.
		
		"""
		# Try reversing philo-root first, since we can't do anything if that fails.
		if CACHE_PHILO_ROOT:
			key = "CACHE_PHILO_ROOT__" + settings.ROOT_URLCONF
			root_url = cache.get(key)
			if root_url is None:
				root_url = reverse('philo-root')
				cache.set(key, root_url)
		else:
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
	
	class Meta(SlugTreeEntity.Meta):
		app_label = 'philo'


# the following line enables the selection of a node as the root for a given django.contrib.sites Site object
models.ForeignKey(Node, related_name='sites', null=True, blank=True).contribute_to_class(Site, 'root_node')


class View(Entity):
	"""
	:class:`View` is an abstract model that represents an item which can be "rendered", generally in response to an :class:`HttpRequest`.
	
	"""
	#: A generic relation back to nodes.
	nodes = generic.GenericRelation(Node, content_type_field='view_content_type', object_id_field='view_object_id')
	
	#: An attribute on the class which defines whether this :class:`View` can handle subpaths. Default: ``False``
	accepts_subpath = False
	
	@classmethod
	def handles_subpath(cls, subpath):
		"""Returns True if the :class:`View` handles the given subpath, and False otherwise."""
		if not cls.accepts_subpath and subpath != "/":
			return False
		return True
	
	def reverse(self, view_name=None, args=None, kwargs=None, node=None, obj=None):
		"""
		If :attr:`accepts_subpath` is True, try to reverse a URL using the given parameters using ``self`` as the urlconf.
		
		If ``obj`` is provided, :meth:`get_reverse_params` will be called and the results will be combined with any ``view_name``, ``args``, and ``kwargs`` that may have been passed in.
		
		:param view_name: The name of the view to be reversed.
		:param args: Extra args for reversing the view.
		:param kwargs: A dictionary of arguments for reversing the view.
		:param node: The node whose subpath this is.
		:param obj: An object to be passed to :meth:`get_reverse_params` to generate a view_name, args, and kwargs for reversal.
		:returns: A subpath beyond the node that reverses the view, or an absolute url that reverses the view if a node was passed in.
		:except philo.exceptions.ViewDoesNotProvideSubpaths: if :attr:`accepts_subpath` is False
		:except philo.exceptions.ViewCanNotProvideSubpath: if a reversal is not possible.
		
		"""
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
		"""
		This method is not implemented on the base class. It should return a (``view_name``, ``args``, ``kwargs``) tuple suitable for reversing a url for the given ``obj`` using ``self`` as the urlconf. If a reversal will not be possible, this method should raise :class:`~philo.exceptions.ViewCanNotProvideSubpath`.
		
		"""
		raise NotImplementedError("View subclasses must implement get_reverse_params to support subpaths.")
	
	def attributes_with_node(self, node, mapper=LazyPassthroughAttributeMapper):
		"""
		Returns a :class:`LazyPassthroughAttributeMapper` which can be used to directly retrieve the values of :class:`Attribute`\ s related to the :class:`View`, falling back on the :class:`Attribute`\ s of the passed-in :class:`Node` and its ancestors.
		
		"""
		return mapper((self, node))
	
	def render_to_response(self, request, extra_context=None):
		"""
		Renders the :class:`View` as an :class:`HttpResponse`. This will raise :const:`~philo.exceptions.MIDDLEWARE_NOT_CONFIGURED` if the `request` doesn't have an attached :class:`Node`. This can happen if the :class:`~philo.middleware.RequestNodeMiddleware` is not in :setting:`settings.MIDDLEWARE_CLASSES` or if it is not functioning correctly.
		
		:meth:`render_to_response` will send the :data:`~philo.signals.view_about_to_render` signal, then call :meth:`actually_render_to_response`, and finally send the :data:`~philo.signals.view_finished_rendering` signal before returning the ``response``.

		"""
		if not hasattr(request, 'node'):
			raise MIDDLEWARE_NOT_CONFIGURED
		
		extra_context = extra_context or {}
		view_about_to_render.send(sender=self, request=request, extra_context=extra_context)
		response = self.actually_render_to_response(request, extra_context)
		view_finished_rendering.send(sender=self, response=response)
		return response
	
	def actually_render_to_response(self, request, extra_context=None):
		"""Concrete subclasses must override this method to provide the business logic for turning a ``request`` and ``extra_context`` into an :class:`HttpResponse`."""
		raise NotImplementedError('View subclasses must implement actually_render_to_response.')
	
	class Meta:
		abstract = True


_view_content_type_limiter.cls = View


class MultiView(View):
	"""
	:class:`MultiView` is an abstract model which represents a section of related pages - for example, a :class:`~philo.contrib.penfield.BlogView` might have a foreign key to :class:`Page`\ s for an index, an entry detail, an entry archive by day, and so on. :class:`!MultiView` subclasses :class:`View`, and defines the following additional methods and attributes:
	
	"""
	#: Same as :attr:`View.accepts_subpath`. Default: ``True``
	accepts_subpath = True
	
	@property
	def urlpatterns(self):
		"""Returns urlpatterns that point to views (generally methods on the class). :class:`MultiView`\ s can be thought of as "managing" these subpaths."""
		raise NotImplementedError("MultiView subclasses must implement urlpatterns.")
	
	def actually_render_to_response(self, request, extra_context=None):
		"""
		Resolves the remaining subpath left after finding this :class:`View`'s node using :attr:`self.urlpatterns <urlpatterns>` and renders the view function (or method) found with the appropriate args and kwargs.
		
		"""
		clear_url_caches()
		subpath = request.node._subpath
		view, args, kwargs = resolve(subpath, urlconf=self)
		view_args = getargspec(view)
		if extra_context is not None and ('extra_context' in view_args[0] or view_args[2] is not None):
			if 'extra_context' in kwargs:
				extra_context.update(kwargs['extra_context'])
			kwargs['extra_context'] = extra_context
		return view(request, *args, **kwargs)
	
	def get_context(self):
		"""Hook for providing instance-specific context - such as the value of a Field - to any view methods on the instance."""
		return {}
	
	def basic_view(self, field_name):
		"""
		Given the name of a field on the class, accesses the value of
		that field and treats it as a ``View`` instance. Creates a
		basic context based on self.get_context() and any extra_context
		that was passed in, then calls the ``View`` instance's
		render_to_response() method. This method is meant to be called
		to return a view function appropriate for urlpatterns.
		
		:param field_name: The name of a field on the instance which contains a :class:`View` subclass instance.
		:returns: A simple view function.
		
		Example::
			
			class Foo(Multiview):
				page = models.ForeignKey(Page)
				
				@property
				def urlpatterns(self):
					urlpatterns = patterns('',
						url(r'^$', self.basic_view('page'))
					)
					return urlpatterns
		
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
	"""An abstract parent class for models which deal in targeting a url."""
	#: An optional :class:`ForeignKey` to a :class:`.Node`. If provided, that node will be used as the basis for the redirect.
	target_node = models.ForeignKey(Node, blank=True, null=True, related_name="%(app_label)s_%(class)s_related")
	#: A :class:`CharField` which may contain an absolute or relative URL, or the name of a node's subpath.
	url_or_subpath = models.CharField(max_length=200, blank=True, help_text="Point to this url or, if a node is defined and accepts subpaths, this subpath of the node.")
	#: A :class:`~philo.models.fields.JSONField` instance. If the value of :attr:`reversing_parameters` is not None, the :attr:`url_or_subpath` will be treated as the name of a view to be reversed. The value of :attr:`reversing_parameters` will be passed into the reversal as args if it is a list or as kwargs if it is a dictionary. Otherwise it will be ignored.
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
	
	def get_target_url(self, memoize=True):
		"""Calculates and returns the target url based on the :attr:`target_node`, :attr:`url_or_subpath`, and :attr:`reversing_parameters`. The results will be memoized by default; this can be prevented by passing in ``memoize=False``."""
		if memoize:
			memo_args = (self.target_node_id, self.url_or_subpath, self.reversing_parameters_json)
			try:
				return self._target_url_memo[memo_args]
			except AttributeError:
				self._target_url_memo = {}
			except KeyError:
				pass
		
		node = self.target_node
		if node is not None and node.accepts_subpath and self.url_or_subpath:
			if self.reversing_parameters is not None:
				view_name, args, kwargs = self.get_reverse_params()
				subpath = node.view.reverse(view_name, args=args, kwargs=kwargs)
			else:
				subpath = self.url_or_subpath
				if subpath[0] != '/':
					subpath = '/' + subpath
			target_url = node.construct_url(subpath)
		elif node is not None:
			target_url = node.get_absolute_url()
		else:
			if self.reversing_parameters is not None:
				view_name, args, kwargs = self.get_reverse_params()
				target_url = reverse(view_name, args=args, kwargs=kwargs)
			else:
				target_url = self.url_or_subpath
		
		if memoize:
			self._target_url_memo[memo_args] = target_url
		return target_url
	target_url = property(get_target_url)
	
	class Meta:
		abstract = True


class Redirect(TargetURLModel, View):
	"""Represents a 301 or 302 redirect to a different url on an absolute or relative path."""
	#: A choices tuple of redirect status codes (temporary or permanent).
	STATUS_CODES = (
		(302, 'Temporary'),
		(301, 'Permanent'),
	)
	#: An :class:`IntegerField` which uses :attr:`STATUS_CODES` as its choices. Determines whether the redirect is considered temporary or permanent.
	status_code = models.IntegerField(choices=STATUS_CODES, default=302, verbose_name='redirect type')
	
	def actually_render_to_response(self, request, extra_context=None):
		"""Returns an :class:`HttpResponseRedirect` to :attr:`self.target_url`."""
		response = HttpResponseRedirect(self.target_url)
		response.status_code = self.status_code
		return response
	
	class Meta:
		app_label = 'philo'


class File(View):
	"""Stores an arbitrary file."""
	#: The name of the uploaded file. This is meant for finding the file again later, not for display.
	name = models.CharField(max_length=255)
	#: Defines the mimetype of the uploaded file. This will not be validated. If no mimetype is provided, it will be automatically generated based on the filename.
	mimetype = models.CharField(max_length=255, blank=True)
	#: Contains the uploaded file. Files are uploaded to ``philo/files/%Y/%m/%d``.
	file = models.FileField(upload_to='philo/files/%Y/%m/%d')
	
	def clean(self):
		if not self.mimetype:
			self.mimetype = mimetypes.guess_type(self.file.name, strict=False)[0]
			if self.mimetype is None:
				raise ValidationError("Unknown file type.")
	
	def actually_render_to_response(self, request, extra_context=None):
		wrapper = FileWrapper(self.file)
		response = HttpResponse(wrapper, content_type=self.mimetype)
		response['Content-Length'] = self.file.size
		response['Content-Disposition'] = "inline; filename=%s" % basename(self.file.name)
		return response
	
	class Meta:
		app_label = 'philo'
	
	def __unicode__(self):
		"""Returns the value of :attr:`File.name`."""
		return self.name


register_value_model(Node)