from django import template
from django.contrib.contenttypes.models import ContentType
from django.conf import settings
from philo.utils import LOADED_TEMPLATE_ATTR


register = template.Library()


class EmbedNode(template.Node):
	def __init__(self, content_type, varname, object_pk=None, template_name=None, kwargs=None):
		assert template_name is not None or object_pk is not None
		self.content_type = content_type
		self.varname = varname
		
		kwargs = kwargs or {}
		for k, v in kwargs.items():
			kwargs[k] = template.Variable(v)
		self.kwargs = kwargs
		
		if object_pk is not None:
			self.object_pk = object_pk
			try:
				self.instance = content_type.get_object_for_this_type(pk=object_pk)
			except content_type.model_class().DoesNotExist:
				self.instance = False
		else:
			self.instance = None
		
		if template_name is not None:
			try:
				self.template = template.loader.get_template(template_name)
			except template.TemplateDoesNotExist:
				self.template = False
		else:
			self.template = None
	
	def render(self, context):
		if self.template_name is not None:
			if self.template is False:
				return settings.TEMPLATE_STRING_IF_INVALID
			
			if self.varname not in context:
				context[self.varname] = {}
			context[self.varname][self.content_type] = self.template
			
			return ''
		
		# Otherwise self.instance should be set. Render the instance with the appropriate template!
		if self.instance is None or self.instance is False:
			return settings.TEMPLATE_STRING_IF_INVALID
		
		try:
			t = context[self.varname][self.content_type]
		except KeyError:
			return settings.TEMPLATE_STRING_IF_INVALID
		
		context.push()
		context['embedded'] = self.instance
		for k, v in self.kwargs.items():
			self.kwargs[k] = v.resolve(context)
		context.update(self.kwargs)
		t_rendered = t.render(context)
		context.pop()
		return t_rendered


def get_embedded(self):
	return template.loader.get_template(self.template_name)


setattr(EmbedNode, LOADED_TEMPLATE_ATTR, property(get_embedded))


def do_embed(parser, token):
	"""
	The {% embed %} tag can be used in three ways:
	{% embed as <varname> %} :: This sets which variable will be used to track embedding template names for the current context. Default: "embed"
	{% embed <app_label>.<model_name> with <template> %} :: Sets which template will be used to render a particular model.
	{% embed <app_label>.<model_name> <object_pk> [<argname>=<value> ...]%} :: Embeds the instance specified by the given parameters in the document with the previously-specified template. Any kwargs provided will be passed into the context of the template.
	"""
	args = token.split_contents()
	tag = args[0]
	
	if len(args) < 2:
		raise template.TemplateSyntaxError('"%s" template tag must have at least three arguments.' % tag)
	elif len(args) == 3 and args[1] == "as":
		parser._embedNodeVarName = args[2]
		return template.defaulttags.CommentNode()
	else:
		if '.' not in args[1]:
			raise template.TemplateSyntaxError('"%s" template tag expects the first argument to be of the form app_label.model' % tag)
		
		app_label, model = args[1].split('.')
		try:
			ct = ContentType.objects.get(app_label=app_label, model=model)
		except ContentType.DoesNotExist:
			raise template.TemplateSyntaxError('"%s" template tag option "references" requires an argument of the form app_label.model which refers to an installed content type (see django.contrib.contenttypes)' % tag)
		
		if args[2] == "with":
			if len(args) > 4:
				raise template.TemplateSyntaxError('"%s" template tag may have no more than four arguments.' % tag)
			
			if args[3][0] not in ['"', "'"] and args[3][-1] not in ['"', "'"]:
				raise template.TemplateSyntaxError('"%s" template tag expects the template name to be in quotes.' % tag)
			if args[3][0] != args[3][-1]:
				raise template.TemplateSyntaxError('"%s" template tag called with non-matching quotes.' % tag)
			
			template_name = args[3].strip('"\'')
			
			return EmbedNode(ct, template_name=template_name, varname=getattr(parser, '_embedNodeVarName', 'embed'))
		object_pk = args[2]
		varname = getattr(parser, '_embedNodeVarName', 'embed')
		
		remaining_args = args[3:]
		kwargs = {}
		for arg in remaining_args:
			if '=' not in arg:
				raise template.TemplateSyntaxError("Invalid keyword argument for '%s' template tag: %s" % (tag, arg))
			k, v = arg.split('=')
			kwargs[k] = v
		
		return EmbedNode(ct, object_pk=object_pk, varname=varname, kwargs=kwargs)


register.tag('embed', do_embed)