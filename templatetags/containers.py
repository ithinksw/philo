from django import template
from django.conf import settings
from django.utils.safestring import SafeUnicode, mark_safe
from django.core.exceptions import ObjectDoesNotExist

register = template.Library()


class ContainerNode(template.Node):
	def __init__(self, name, as_var=None):
		self.name = name
		self.as_var = as_var
	def render(self, context):
		page = None
		if 'page' in context:
			page = context['page']
		if page:
			contentlet = None
			try:
				contentlet = page.contentlets.get(name__exact=self.name)
			except ObjectDoesNotExist:
				pass
			if contentlet:
				content = contentlet.content
				if contentlet.dynamic:
					try:
						content = mark_safe(template.Template(content, name=contentlet.name).render(context))
					except template.TemplateSyntaxError, error:
						content = ''
						if settings.DEBUG:
							content = ('[Error parsing contentlet \'%s\': %s]' % self.name, error)
				if self.as_var:
					context[self.as_var] = content
					content = ''
				return content
		return ''


def do_container(parser, token):
	"""
	{% container <name> [as <variable>] %}
	"""
	params = token.split_contents()
	if len(params) >= 2: # without as_var
		name = params[1].strip('"')
		as_var = None
		if len(params) == 4:
			as_var = params[3]
		return ContainerNode(name, as_var)
	else: # error
		raise template.TemplateSyntaxError('do_container template tag provided with invalid arguments')
register.tag('container', do_container)
