"""
The container template tags are automatically included as builtins if :mod:`philo` is an installed app.

"""

from django import template
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from django.utils.safestring import SafeUnicode, mark_safe


register = template.Library()


CONTAINER_CONTEXT_KEY = 'philo_container_context'


class ContainerContext(object):
	def __init__(self, page):
		self.page = page
	
	def get_contentlets(self):
		if not hasattr(self, '_contentlets'):
			self._contentlets = dict(((c.name, c) for c in self.page.contentlets.all()))
		return self._contentlets
	
	def get_references(self):
		if not hasattr(self, '_references'):
			references = self.page.contentreferences.all()
			self._references = dict((((c.name, ContentType.objects.get_for_id(c.content_type_id)), c) for c in references))
		return self._references


class ContainerNode(template.Node):
	def __init__(self, name, references=None, as_var=None):
		self.name = name
		self.as_var = as_var
		self.references = references
	
	def render(self, context):
		container_content = self.get_container_content(context)
		
		if self.as_var:
			context[self.as_var] = container_content
			return ''
		
		return container_content
	
	def get_container_content(self, context):
		try:
			container_context = context.render_context[CONTAINER_CONTEXT_KEY]
		except KeyError:
			try:
				page = context['page']
			except KeyError:
				return settings.TEMPLATE_STRING_IF_INVALID
			
			container_context = ContainerContext(page)
			context.render_context[CONTAINER_CONTEXT_KEY] = container_context
		
		if self.references:
			# Then it's a content reference.
			try:
				contentreference = container_context.get_references()[(self.name, self.references)]
			except KeyError:
				content = ''
			else:
				content = contentreference.content
		else:
			# Otherwise it's a contentlet.
			try:
				contentlet = container_context.get_contentlets()[self.name]
			except KeyError:
				content = ''
			else:
				content = contentlet.content
		return content


@register.tag
def container(parser, token):
	"""
	If a template using this tag is used to render a :class:`.Page`, that :class:`.Page` will have associated content which can be set in the admin interface. If a content type is referenced, then a :class:`.ContentReference` object will be created; otherwise, a :class:`.Contentlet` object will be created.
	
	Usage::
	
		{% container <name> [[references <app_label>.<model_name>] as <variable>] %}
	
	"""
	params = token.split_contents()
	if len(params) >= 2:
		tag = params[0]
		name = params[1].strip('"')
		references = None
		as_var = None
		if len(params) > 2:
			remaining_tokens = params[2:]
			while remaining_tokens:
				option_token = remaining_tokens.pop(0)
				if option_token == 'references':
					try:
						app_label, model = remaining_tokens.pop(0).strip('"').split('.')
						references = ContentType.objects.get_by_natural_key(app_label, model)
					except IndexError:
						raise template.TemplateSyntaxError('"%s" template tag option "references" requires an argument specifying a content type' % tag)
					except ValueError:
						raise template.TemplateSyntaxError('"%s" template tag option "references" requires an argument of the form app_label.model (see django.contrib.contenttypes)' % tag)
					except ObjectDoesNotExist:
						raise template.TemplateSyntaxError('"%s" template tag option "references" requires an argument of the form app_label.model which refers to an installed content type (see django.contrib.contenttypes)' % tag)
				elif option_token == 'as':
					try:
						as_var = remaining_tokens.pop(0)
					except IndexError:
						raise template.TemplateSyntaxError('"%s" template tag option "as" requires an argument specifying a variable name' % tag)
			if references and not as_var:
				raise template.TemplateSyntaxError('"%s" template tags using "references" option require additional use of the "as" option specifying a variable name' % tag)
		return ContainerNode(name, references, as_var)
		
	else: # error
		raise template.TemplateSyntaxError('"%s" template tag provided without arguments (at least one required)' % tag)
