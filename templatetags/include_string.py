from django import template
from django.conf import settings


register = template.Library()


class IncludeStringNode(template.Node):
	"""The passed variable is expected to be a string of template code to be rendered with
	the current context."""
	def __init__(self, string):
		self.string = string
	
	def render(self, context):
		try:
			t = template.Template(self.string.resolve(context))
			return t.render(context)
		except template.TemplateSyntaxError:
			if settings.TEMPLATE_DEBUG:
				raise
			return settings.TEMPLATE_STRING_IF_INVALID
		except:
			return settings.TEMPLATE_STRING_IF_INVALID


def do_include_string(parser, token):
	"""
	Include a flat string by interpreting it as a template.
	{% include_string <template_code> %}
	"""
	bits = token.split_contents()
	if len(bits) != 2:
		raise TemplateSyntaxError("%r tag takes one argument: the template string to be included" % bits[0])
 	string = parser.compile_filter(bits[1])
	return IncludeStringNode(string)


register.tag('include_string', do_include_string)