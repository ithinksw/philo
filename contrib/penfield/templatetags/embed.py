from django import template
from django.contrib.contenttypes.models import ContentType
from django.conf import settings


register = template.Library()


class EmbedNode(template.Node):
	def __init__(self, model, varname, object_pk=None, template_name=None):
		assert template_name is not None or object_pk is not None
		app_label, model = model.split('.')
		self.model = ContentType.objects.get(app_label=app_label, model=model).model_class()
		self.varname = varname
		self.object_pk = object_pk
		self.template_name = template_name
	
	def render(self, context):
		if self.template_name is not None:
			template_name = self.template_name.resolve(context)
		
			try:
				t = template.loader.get_template(template_name)
			except template.TemplateDoesNotExist:
				return settings.TEMPLATE_STRING_IF_INVALID
			else:
				if self.varname not in context:
					context[self.varname] = {}
				context[self.varname][self.model] = t
			return ''
		
		# Otherwise self.object_pk is set. Render the instance with the appropriate template!
		try:
			instance = self.model.objects.get(pk=self.object_pk.resolve(context))
		except self.model.DoesNotExist:
			return settings.TEMPLATE_STRING_IF_INVALID
		
		try:
			t = context[self.varname][self.model]
		except KeyError:
			return settings.TEMPLATE_STRING_IF_INVALID
		
		context.push()
		context['embedded'] = instance
		t_rendered = t.render(context)
		context.pop()
		return t_rendered


def do_embed(parser, token):
	"""
	The {% embed %} tag can be used in three ways:
	{% embed as <varname> %} :: This sets which variable will be used to track embedding template names for the current context. Default: "embed"
	{% embed <app_label>.<model_name> with <template> %} :: Sets which template will be used to render a particular model.
	{% embed <app_label>.<model_name> <object_pk> %} :: Embeds the instance specified by the given parameters in the document with the previously-specified template.
	"""
	args = token.split_contents()
	tag = args[0]
	
	if len(args) < 2:
		raise template.TemplateSyntaxError('"%s" template tag must have at least three arguments.' % tag)
	elif len(args) > 4:
		raise template.TemplateSyntaxError('"%s" template tag may have no more than four arguments.' % tag)
	else:
		if len(args) == 3 and args[1] == "as":
			parser._embedNodeVarName = args[2]
			return template.defaulttags.CommentNode()
		
		if '.' not in args[1]:
			raise template.TemplateSyntaxError('"%s" template tag expects the first argument to be of the type app_label.model' % tag)
		
		if len(args) == 3:
			return EmbedNode(args[1], object_pk=args[2], varname=getattr(parser, '_embedNodeVarName', 'embed'))
		else:
			# 3 args
			if args[2] != "with":
				raise template.TemplateSyntaxError('"%s" template tag requires the second of three arguments to be "with"' % tag)
			
			if args[3][0] not in ['"', "'"] and args[3][-1] not in ['"', "'"]:
				raise template.TemplateSyntaxError('"%s" template tag expects the template name to be in quotes.' % tag)
			if args[3][0] != args[3][-1]:
				raise template.TemplateSyntaxError('"%s" template tag called with non-matching quotes.' % tag)
			
			template_name = args[3].strip('"\'')
			
			return EmbedNode(args[1], template_name=template_name, varname=getattr(parser, '_embedNodeVarName', 'embed'))


register.tag('embed', do_embed)