from django import template
from django.contrib.contenttypes.models import ContentType
from django.conf import settings
from django.template.loader_tags import ExtendsNode, BlockContext, BLOCK_CONTEXT_KEY, TextNode, BlockNode
from philo.utils import LOADED_TEMPLATE_ATTR


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
		embeds = self.embeds[embed.content_type]
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
				embeds = embed_context.embeds[embed.content_type][:len(embed_context.rendered)][::-1]
				for e in embeds:
					template = e.get_template(context)
					if template:
						return template
		
		raise IndexError


# Override ExtendsNode render method to have it handle EmbedNodes
# similarly to BlockNodes.
old_extends_node_init = ExtendsNode.__init__


def get_embed_dict(nodelist):
	embeds = {}
	for n in nodelist.get_nodes_by_type(ConstantEmbedNode):
		if n.content_type not in embeds:
			embeds[n.content_type] = [n]
		else:
			embeds[n.content_type].append(n)
	return embeds


def extends_node_init(self, nodelist, *args, **kwargs):
	self.embeds = get_embed_dict(nodelist)
	old_extends_node_init(self, nodelist, *args, **kwargs)


def render_extends_node(self, context):
	compiled_parent = self.get_parent(context)
	
	if BLOCK_CONTEXT_KEY not in context.render_context:
		context.render_context[BLOCK_CONTEXT_KEY] = BlockContext()
	block_context = context.render_context[BLOCK_CONTEXT_KEY]
	
	if EMBED_CONTEXT_KEY not in context.render_context:
		context.render_context[EMBED_CONTEXT_KEY] = EmbedContext()
	embed_context = context.render_context[EMBED_CONTEXT_KEY]
	
	# Add the block nodes from this node to the block context
	# Do the equivalent for embed nodes
	block_context.add_blocks(self.blocks)
	embed_context.add_embeds(self.embeds)
	
	# If this block's parent doesn't have an extends node it is the root,
	# and its block nodes also need to be added to the block context.
	for node in compiled_parent.nodelist:
		# The ExtendsNode has to be the first non-text node.
		if not isinstance(node, TextNode):
			if not isinstance(node, ExtendsNode):
				blocks = dict([(n.name, n) for n in compiled_parent.nodelist.get_nodes_by_type(BlockNode)])
				block_context.add_blocks(blocks)
				embeds = get_embed_dict(compiled_parent.nodelist)
				embed_context.add_embeds(embeds)
			break

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
	
	def compile_instance(self, object_pk, context=None):
		self.object_pk = object_pk
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
	
	def compile_template(self, template_name, context=None):
		try:
			return template.loader.get_template(template_name)
		except template.TemplateDoesNotExist:
			if not hasattr(self, 'template_name') and settings.TEMPLATE_DEBUG:
				# Then it's a constant node.
				raise
			return False
	
	def get_template(self, context):
		return self.template
	
	def check_context(self, context):
		if EMBED_CONTEXT_KEY not in context.render_context:
			context.render_context[EMBED_CONTEXT_KEY] = EmbedContext()
		embed_context = context.render_context[EMBED_CONTEXT_KEY]
		
		
		if self.content_type not in embed_context.embeds:
			embed_context.embeds[self.content_type] = [self]
		elif self not in embed_context.embeds[self.content_type]:
			embed_context.embeds[self.content_type].append(self)
	
	def mark_rendered(self, context):
		context.render_context[EMBED_CONTEXT_KEY].rendered.append(self)
	
	def render(self, context):
		self.check_context(context)
		
		if self.template is not None:
			if self.template is False:
				return settings.TEMPLATE_STRING_IF_INVALID
			self.mark_rendered(context)
			return ''
		
		# Otherwise self.instance should be set. Render the instance with the appropriate template!
		if self.instance is None or self.instance is False:
			self.mark_rendered(context)
			return settings.TEMPLATE_STRING_IF_INVALID
		
		return self.render_instance(context, self.instance)
	
	def render_instance(self, context, instance):
		try:
			t = context.render_context[EMBED_CONTEXT_KEY].get_embed_template(self, context)
		except (KeyError, IndexError):
			if settings.TEMPLATE_DEBUG:
				raise
			return settings.TEMPLATE_STRING_IF_INVALID
		
		context.push()
		context['embedded'] = instance
		kwargs = {}
		for k, v in self.kwargs.items():
			kwargs[k] = v.resolve(context)
		context.update(kwargs)
		t_rendered = t.render(context)
		context.pop()
		self.mark_rendered(context)
		return t_rendered


class EmbedNode(ConstantEmbedNode):
	def __init__(self, content_type, object_pk=None, template_name=None, kwargs=None):
		assert template_name is not None or object_pk is not None
		self.content_type = content_type
		
		kwargs = kwargs or {}
		for k, v in kwargs.items():
			kwargs[k] = v
		self.kwargs = kwargs
		
		if object_pk is not None:
			self.object_pk = object_pk
		else:
			self.object_pk = None
			self.instance = None
		
		if template_name is not None:
			self.template_name = template_name
		else:
			self.template_name = None
			self.template = None
	
	def get_instance(self, context):
		return self.compile_instance(self.object_pk, context)
	
	def get_template(self, context):
		return self.compile_template(self.template_name, context)
	
	def render(self, context):
		self.check_context(context)
		
		if self.template_name is not None:
			self.mark_rendered(context)
			return ''
		
		if self.object_pk is None:
			if settings.TEMPLATE_DEBUG:
				raise ValueError("NoneType is not a valid object_pk value")
			self.mark_rendered(context)
			return settings.TEMPLATE_STRING_IF_INVALID
		
		instance = self.compile_instance(self.object_pk.resolve(context))
		
		return self.render_instance(context, instance)


def get_embedded(self):
	return self.template


setattr(ConstantEmbedNode, LOADED_TEMPLATE_ATTR, property(get_embedded))


def do_embed(parser, token):
	"""
	The {% embed %} tag can be used in two ways:
	{% embed <app_label>.<model_name> with <template> %} :: Sets which template will be used to render a particular model.
	{% embed <app_label>.<model_name> <object_pk> [<argname>=<value> ...]%} :: Embeds the instance specified by the given parameters in the document with the previously-specified template. Any kwargs provided will be passed into the context of the template.
	"""
	args = token.split_contents()
	tag = args[0]
	
	if len(args) < 2:
		raise template.TemplateSyntaxError('"%s" template tag must have at least three arguments.' % tag)
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
			
			if args[3][0] in ['"', "'"] and args[3][0] == args[3][-1]:
				return ConstantEmbedNode(ct, template_name=args[3])
			
			return EmbedNode(ct, template_name=args[3])
		
		object_pk = args[2]
		remaining_args = args[3:]
		kwargs = {}
		for arg in remaining_args:
			if '=' not in arg:
				raise template.TemplateSyntaxError("Invalid keyword argument for '%s' template tag: %s" % (tag, arg))
			k, v = arg.split('=')
			kwargs[k] = parser.compile_filter(v)
		
		try:
			int(object_pk)
		except ValueError:
			return EmbedNode(ct, object_pk=parser.compile_filter(object_pk), kwargs=kwargs)
		else:
			return ConstantEmbedNode(ct, object_pk=object_pk, kwargs=kwargs)


register.tag('embed', do_embed)