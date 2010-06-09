from django import template
from django.conf import settings
from django.utils.safestring import SafeUnicode, mark_safe
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.contenttypes.models import ContentType


register = template.Library()


class ContainerNode(template.Node):
	def __init__(self, name, references=None, as_var=None, nodelist_main=None, nodelist_empty=None):
		self.name = name
		self.as_var = as_var
		self.references = references
		self.nodelist_main = nodelist_main
		self.nodelist_empty = nodelist_empty
		
	def render(self, context):
		content = settings.TEMPLATE_STRING_IF_INVALID
		if 'page' in context:
			container_content = self.get_container_content(context['page'])
		
		if self.nodelist_main is None:
			if container_content and self.as_var:
				context[self.as_var] = container_content
				return ''
			return container_content
		
		if container_content:
			if self.as_var is None:
				self.as_var = self.name
			context.push()
			context[self.as_var] = container_content
			return nodelist_main.render(context)
		
		if nodelist_empty is not None:
			return nodelist_empty.render(context)
		
		return ''
	
	def get_container_content(self, page):
		if self.references:
			try:
				contentreference = page.contentreferences.get(name__exact=self.name, content_type=self.references)
				content = contentreference.content
			except ObjectDoesNotExist:
				content = ''
		else:
			try:
				contentlet = page.contentlets.get(name__exact=self.name)
				if contentlet.dynamic:
					try:
						content = mark_safe(template.Template(contentlet.content, name=contentlet.name).render(context))
					except template.TemplateSyntaxError, error:
						if settings.DEBUG:
							content = ('[Error parsing contentlet \'%s\': %s]' % self.name, error)
				else:
					content = contentlet.content
			except ObjectDoesNotExist:
				content = ''
		return content

def do_container(parser, token):
	"""
	{% container <name> [[references <type>] as <variable>] %} 
	{% blockcontainer <name> [[references <type>] as <variable>] %} [ {% empty %} ] {% endblockcontainer %}
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
						references = ContentType.objects.get(app_label=app_label, model=model)
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
		if tag == 'container':
			return ContainerNode(name, references, as_var)
		
		nodelist_main = parser.parse(('empty','endblockcontainer',))
		token = parser.next_token()
		
		if token.contents == 'empty':
			nodelist_empty = parser.parse(('endblockcontainer',))
			parser.delete_first_token()
		else:
			nodelist_empty = None
		return BlockContainerNode(name, references, as_var, nodelist_main, nodelist_empty)
		
	else: # error
		raise template.TemplateSyntaxError('"%s" template tag provided without arguments (at least one required)' % tag)
register.tag('container', do_container)