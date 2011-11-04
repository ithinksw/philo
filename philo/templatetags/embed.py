"""
The embed template tags are automatically included as builtins if :mod:`philo` is an installed app.

"""
from django import template
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.template.loader_tags import ExtendsNode, BlockContext, BLOCK_CONTEXT_KEY, TextNode, BlockNode

from philo.utils.templates import LOADED_TEMPLATE_ATTR


register = template.Library()
EMBED_CONTEXT_KEY = 'embed_context'


class EmbedContext(object):
	"Inspired by django.template.loader_tags.BlockContext."
	def __init__(self):
		self.embeds = {}
		self.rendered = []
	
	def add_embeds(self, embeds):
		for content_type, embed_list in embeds.iteritems():
			if content_type in self.embeds:
				self.embeds[content_type] = embed_list + self.embeds[content_type]
			else:
				self.embeds[content_type] = embed_list
	
	def get_embed_template(self, embed, context):
		"""To return a template for an embed node, find the node's position in the stack
		and then progress up the stack until a template-defining node is found
		"""
		ct = embed.get_content_type(context)
		embeds = self.embeds[ct]
		embeds = embeds[:embeds.index(embed)][::-1]
		for e in embeds:
			template = e.get_template(context)
			if template:
				return template
		
		# No template was found in the current render_context - but perhaps one level up? Or more?
		# We may be in an inclusion tag.
		self_found = False
		for context_dict in context.render_context.dicts[::-1]:
			if not self_found:
				if self in context_dict.values():
					self_found = True
					continue
			elif EMBED_CONTEXT_KEY not in context_dict:
				continue
			else:
				embed_context = context_dict[EMBED_CONTEXT_KEY]
				# We can tell where we are in the list of embeds by which have already been rendered.
				embeds = embed_context.embeds[ct][:len(embed_context.rendered)][::-1]
				for e in embeds:
					template = e.get_template(context)
					if template:
						return template
		
		raise IndexError


# Override ExtendsNode render method to have it handle EmbedNodes
# similarly to BlockNodes.
old_extends_node_init = ExtendsNode.__init__


def get_embed_dict(embed_list, context):
	embeds = {}
	for e in embed_list:
		ct = e.get_content_type(context)
		if ct is None:
			# Then the embed doesn't exist for this context.
			continue
		if ct not in embeds:
			embeds[ct] = [e]
		else:
			embeds[ct].append(e)
	return embeds


def extends_node_init(self, nodelist, *args, **kwargs):
	self.embed_list = nodelist.get_nodes_by_type(ConstantEmbedNode)
	old_extends_node_init(self, nodelist, *args, **kwargs)


def render_extends_node(self, context):
	compiled_parent = self.get_parent(context)
	embeds = get_embed_dict(self.embed_list, context)
	
	if BLOCK_CONTEXT_KEY not in context.render_context:
		context.render_context[BLOCK_CONTEXT_KEY] = BlockContext()
	block_context = context.render_context[BLOCK_CONTEXT_KEY]
	
	if EMBED_CONTEXT_KEY not in context.render_context:
		context.render_context[EMBED_CONTEXT_KEY] = EmbedContext()
	embed_context = context.render_context[EMBED_CONTEXT_KEY]
	
	# Add the block nodes from this node to the block context
	# Do the equivalent for embed nodes
	block_context.add_blocks(self.blocks)
	embed_context.add_embeds(embeds)
	
	# If this block's parent doesn't have an extends node it is the root,
	# and its block nodes also need to be added to the block context.
	for node in compiled_parent.nodelist:
		# The ExtendsNode has to be the first non-text node.
		if not isinstance(node, TextNode):
			if not isinstance(node, ExtendsNode):
				blocks = dict([(n.name, n) for n in compiled_parent.nodelist.get_nodes_by_type(BlockNode)])
				block_context.add_blocks(blocks)
				embeds = get_embed_dict(compiled_parent.nodelist.get_nodes_by_type(ConstantEmbedNode), context)
				embed_context.add_embeds(embeds)
			break
	
	# Explicitly render all direct embed children of this node.
	if self.embed_list:
		for node in self.nodelist:
			if isinstance(node, ConstantEmbedNode):
				node.render(context)
	
	# Call Template._render explicitly so the parser context stays
	# the same.
	return compiled_parent._render(context)


ExtendsNode.__init__ = extends_node_init
ExtendsNode.render = render_extends_node


class ConstantEmbedNode(template.Node):
	"""Analogous to the ConstantIncludeNode, this node precompiles several variables necessary for correct rendering - namely the referenced instance or the included template."""
	def __init__(self, content_type, object_pk=None, template_name=None, kwargs=None):
		assert template_name is not None or object_pk is not None
		self.content_type = content_type
		
		kwargs = kwargs or {}
		for k, v in kwargs.items():
			kwargs[k] = v
		self.kwargs = kwargs
		
		if object_pk is not None:
			self.instance = self.compile_instance(object_pk)
		else:
			self.instance = None
		
		if template_name is not None:
			self.template = self.compile_template(template_name[1:-1])
		else:
			self.template = None
	
	def compile_instance(self, object_pk):
		model = self.content_type.model_class()
		try:
			return model.objects.get(pk=object_pk)
		except model.DoesNotExist:
			if not hasattr(self, 'object_pk') and settings.TEMPLATE_DEBUG:
				# Then it's a constant node.
				raise
			return False
	
	def get_instance(self, context):
		return self.instance
	
	def compile_template(self, template_name):
		try:
			return template.loader.get_template(template_name)
		except template.TemplateDoesNotExist:
			if hasattr(self, 'template') and settings.TEMPLATE_DEBUG:
				# Then it's a constant node.
				raise
			return False
	
	def get_template(self, context):
		return self.template
	
	def get_content_type(self, context):
		return self.content_type
	
	def check_context(self, context):
		if EMBED_CONTEXT_KEY not in context.render_context:
			context.render_context[EMBED_CONTEXT_KEY] = EmbedContext()
		embed_context = context.render_context[EMBED_CONTEXT_KEY]
		
		ct = self.get_content_type(context)
		if ct not in embed_context.embeds:
			embed_context.embeds[ct] = [self]
		elif self not in embed_context.embeds[ct]:
			embed_context.embeds[ct].append(self)
	
	def mark_rendered_for(self, context):
		context.render_context[EMBED_CONTEXT_KEY].rendered.append(self)
	
	def render(self, context):
		self.check_context(context)
		
		template = self.get_template(context)
		if template is not None:
			self.mark_rendered_for(context)
			if template is False:
				return settings.TEMPLATE_STRING_IF_INVALID
			return ''
		
		# Otherwise an instance should be available. Render the instance with the appropriate template!
		instance = self.get_instance(context)
		if instance is None or instance is False:
			self.mark_rendered_for(context)
			return settings.TEMPLATE_STRING_IF_INVALID
		
		return self.render_instance(context, instance)
	
	def render_instance(self, context, instance):
		try:
			t = context.render_context[EMBED_CONTEXT_KEY].get_embed_template(self, context)
		except (KeyError, IndexError):
			self.mark_rendered_for(context)
			return settings.TEMPLATE_STRING_IF_INVALID
		
		context.push()
		context['embedded'] = instance
		for k, v in self.kwargs.items():
			context[k] = v.resolve(context)
		t_rendered = t.render(context)
		context.pop()
		self.mark_rendered_for(context)
		return t_rendered


class EmbedNode(ConstantEmbedNode):
	def __init__(self, content_type, object_pk=None, template_name=None, kwargs=None):
		assert template_name is not None or object_pk is not None
		self.content_type = content_type
		self.kwargs = kwargs or {}
		
		if object_pk is not None:
			self.object_pk = object_pk
		else:
			self.object_pk = None
		
		if template_name is not None:
			self.template_name = template_name
		else:
			self.template_name = None
	
	def get_instance(self, context):
		if self.object_pk is None:
			return None
		return self.compile_instance(self.object_pk.resolve(context))
	
	def get_template(self, context):
		if self.template_name is None:
			return None
		return self.compile_template(self.template_name.resolve(context))


class InstanceEmbedNode(EmbedNode):
	def __init__(self, instance, kwargs=None):
		self.instance = instance
		self.kwargs = kwargs or {}
	
	def get_template(self, context):
		return None
	
	def get_instance(self, context):
		return self.instance.resolve(context)
	
	def get_content_type(self, context):
		instance = self.get_instance(context)
		if not instance:
			return None
		return ContentType.objects.get_for_model(instance)


def get_embedded(self):
	return self.template


setattr(ConstantEmbedNode, LOADED_TEMPLATE_ATTR, property(get_embedded))


def parse_content_type(bit, tagname):
	try:
		app_label, model = bit.split('.')
	except ValueError:
		raise template.TemplateSyntaxError('"%s" template tag expects the first argument to be of the form app_label.model' % tagname)
	try:
		ct = ContentType.objects.get_by_natural_key(app_label, model)
	except ContentType.DoesNotExist:
		raise template.TemplateSyntaxError('"%s" template tag requires an argument of the form app_label.model which refers to an installed content type (see django.contrib.contenttypes)' % tagname)
	return ct


@register.tag
def embed(parser, token):
	"""
	The {% embed %} tag can be used in two ways.
	
	First, to set which template will be used to render a particular model. This declaration can be placed in a base template and will propagate into all templates that extend that template.
	
	Syntax::
	
		{% embed <app_label>.<model_name> with <template> %}
	
	Second, to embed a specific model instance in the document with a template specified earlier in the template or in a parent template using the first syntax. The instance can be specified as a content type and pk or as a context variable. Any kwargs provided will be passed into the context of the template.
	
	Syntax::
	
		{% embed (<app_label>.<model_name> <object_pk> || <instance>) [<argname>=<value> ...] %}
	
	"""
	bits = token.split_contents()
	tag = bits.pop(0)
	
	if len(bits) < 1:
		raise template.TemplateSyntaxError('"%s" template tag must have at least two arguments.' % tag)
	
	if len(bits) == 3 and bits[-2] == 'with':
		ct = parse_content_type(bits[0], tag)
		
		if bits[2][0] in ['"', "'"] and bits[2][0] == bits[2][-1]:
			return ConstantEmbedNode(ct, template_name=bits[2])
		return EmbedNode(ct, template_name=bits[2])
	
	# Otherwise they're trying to embed a certain instance.
	kwargs = {}
	try:
		bit = bits.pop()
		while '=' in bit:
			k, v = bit.split('=')
			kwargs[k] = parser.compile_filter(v)
			bit = bits.pop()
		bits.append(bit)
	except IndexError:
		raise template.TemplateSyntaxError('"%s" template tag expects at least one non-keyword argument when embedding instances.')
	
	if len(bits) == 1:
		instance = parser.compile_filter(bits[0])
		return InstanceEmbedNode(instance, kwargs)
	elif len(bits) > 2:
		raise template.TemplateSyntaxError('"%s" template tag expects at most 2 non-keyword arguments when embedding instances.')
	ct = parse_content_type(bits[0], tag)
	pk = bits[1]
	
	try:
		int(pk)
	except ValueError:
		return EmbedNode(ct, object_pk=parser.compile_filter(pk), kwargs=kwargs)
	else:
		return ConstantEmbedNode(ct, object_pk=pk, kwargs=kwargs)