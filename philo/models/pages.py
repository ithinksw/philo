# encoding: utf-8
"""
:class:`Page`\ s are the most frequently used :class:`.View` subclass. They define a basic HTML page and its associated content. Each :class:`Page` renders itself according to a :class:`Template`. The :class:`Template` may contain :ttag:`container` tags, which define related :class:`Contentlet`\ s and :class:`ContentReference`\ s for any page using that :class:`Template`.

"""

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic
from django.core.exceptions import ValidationError
from django.db import models
from django.http import HttpResponse
from django.template import Context, RequestContext, Template as DjangoTemplate

from philo.models.base import SlugTreeEntity, register_value_model
from philo.models.fields import TemplateField
from philo.models.nodes import View
from philo.signals import page_about_to_render_to_string, page_finished_rendering_to_string
from philo.utils import templates


__all__ = ('Template', 'Page', 'Contentlet', 'ContentReference')


class Template(SlugTreeEntity):
	"""Represents a database-driven django template."""
	#: The name of the template. Used for organization and debugging.
	name = models.CharField(max_length=255)
	#: Can be used to let users know what the template is meant to be used for.
	documentation = models.TextField(null=True, blank=True)
	#: Defines the mimetype of the template. This is not validated. Default: ``text/html``.
	mimetype = models.CharField(max_length=255, default=getattr(settings, 'DEFAULT_CONTENT_TYPE', 'text/html'))
	#: An insecure :class:`~philo.models.fields.TemplateField` containing the django template code for this template.
	code = TemplateField(secure=False, verbose_name='django template code')
	
	def get_containers(self):
		"""
		Returns a tuple where the first item is a list of names of contentlets referenced by containers, and the second item is a list of tuples of names and contenttypes of contentreferences referenced by containers. This will break if there is a recursive extends or includes in the template code. Due to the use of an empty Context, any extends or include tags with dynamic arguments probably won't work.
		
		"""
		template = DjangoTemplate(self.code)
		return templates.get_containers(template)
	containers = property(get_containers)
	
	def __unicode__(self):
		"""Returns the value of the :attr:`name` field."""
		return self.name
	
	class Meta(SlugTreeEntity.Meta):
		app_label = 'philo'


class Page(View):
	"""
	Represents a page - something which is rendered according to a :class:`Template`. The page will have a number of related :class:`Contentlet`\ s and :class:`ContentReference`\ s depending on the template selected - but these will appear only after the page has been saved with that template.
	
	"""
	#: A :class:`ForeignKey` to the :class:`Template` used to render this :class:`Page`.
	template = models.ForeignKey(Template, related_name='pages')
	#: The name of this page. Chances are this will be used for organization - i.e. finding the page in a list of pages - rather than for display.
	title = models.CharField(max_length=255)
	
	def get_containers(self):
		"""
		Returns the results :attr:`~Template.containers` for the related template. This is a tuple containing the specs of all :ttag:`container`\ s in the :class:`Template`'s code. The value will be cached on the instance so that multiple accesses will be less expensive.
		
		"""
		if not hasattr(self, '_containers'):
			self._containers = self.template.containers
		return self._containers
	containers = property(get_containers)
	
	def render_to_string(self, request=None, extra_context=None):
		"""
		In addition to rendering as an :class:`HttpResponse`, a :class:`Page` can also render as a string. This means, for example, that :class:`Page`\ s can be used to render emails or other non-HTML content with the same :ttag:`container`-based functionality as is used for HTML.
		
		The :class:`Page` will add itself to the context as ``page`` and its :attr:`~.Entity.attributes` as ``attributes``. If a request is provided, then :class:`request.node <.Node>` will also be added to the context as ``node`` and ``attributes`` will be set to the result of calling :meth:`~.View.attributes_with_node` with that :class:`.Node`.
		
		"""
		context = {}
		context.update(extra_context or {})
		context.update({'page': self, 'attributes': self.attributes})
		template = DjangoTemplate(self.template.code)
		if request:
			context.update({'node': request.node, 'attributes': self.attributes_with_node(request.node)})
			page_about_to_render_to_string.send(sender=self, request=request, extra_context=context)
			string = template.render(RequestContext(request, context))
		else:
			page_about_to_render_to_string.send(sender=self, request=request, extra_context=context)
		 	string = template.render(Context(context))
		page_finished_rendering_to_string.send(sender=self, string=string)
		return string
	
	def actually_render_to_response(self, request, extra_context=None):
		"""Returns an :class:`HttpResponse` with the content of the :meth:`render_to_string` method and the mimetype set to the :attr:`~Template.mimetype` of the related :class:`Template`."""
		return HttpResponse(self.render_to_string(request, extra_context), mimetype=self.template.mimetype)
	
	def __unicode__(self):
		"""Returns the value of :attr:`title`"""
		return self.title
	
	def clean_fields(self, exclude=None):
		"""
		This is an override of the default model clean_fields method. Essentially, in addition to validating the fields, this method validates the :class:`Template` instance that is used to render this :class:`Page`. This is useful for catching template errors before they show up as 500 errors on a live site.
		
		"""
		if exclude is None:
			exclude = []
		
		try:
			super(Page, self).clean_fields(exclude)
		except ValidationError, e:
			errors = e.message_dict
		else:
			errors = {}
		
		if 'template' not in errors and 'template' not in exclude:
			try:
				self.template.clean_fields()
				self.template.clean()
			except ValidationError, e:
				errors['template'] = e.messages
		
		if errors:
			raise ValidationError(errors)
	
	class Meta:
		app_label = 'philo'


class Contentlet(models.Model):
	"""Represents a piece of content on a page. This content is treated as a secure :class:`~philo.models.fields.TemplateField`."""
	#: The page which this :class:`Contentlet` is related to.
	page = models.ForeignKey(Page, related_name='contentlets')
	#: This represents the name of the container as defined by a :ttag:`container` tag.
	name = models.CharField(max_length=255, db_index=True)
	#: A secure :class:`~philo.models.fields.TemplateField` holding the content for this :class:`Contentlet`. Note that actually using this field as a template requires use of the :ttag:`include_string` template tag.
	content = TemplateField()
	
	def __unicode__(self):
		"""Returns the value of the :attr:`name` field."""
		return self.name
	
	class Meta:
		app_label = 'philo'


class ContentReference(models.Model):
	"""Represents a model instance related to a page."""
	#: The page which this :class:`ContentReference` is related to.
	page = models.ForeignKey(Page, related_name='contentreferences')
	#: This represents the name of the container as defined by a :ttag:`container` tag.
	name = models.CharField(max_length=255, db_index=True)
	content_type = models.ForeignKey(ContentType, verbose_name='Content type')
	content_id = models.PositiveIntegerField(verbose_name='Content ID', blank=True, null=True)
	#: A :class:`GenericForeignKey` to a model instance. The content type of this instance is defined by the :ttag:`container` tag which defines this :class:`ContentReference`.
	content = generic.GenericForeignKey('content_type', 'content_id')
	
	def __unicode__(self):
		"""Returns the value of the :attr:`name` field."""
		return self.name
	
	class Meta:
		app_label = 'philo'


register_value_model(Template)
register_value_model(Page)