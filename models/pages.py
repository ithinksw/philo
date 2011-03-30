# encoding: utf-8
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic
from django.core.exceptions import ValidationError
from django.db import models
from django.http import HttpResponse
from django.template import TemplateDoesNotExist, Context, RequestContext, Template as DjangoTemplate, add_to_builtins as register_templatetags, TextNode, VariableNode
from django.template.loader_tags import BlockNode, ExtendsNode, BlockContext
from django.utils.datastructures import SortedDict
from philo.models.base import TreeModel, register_value_model
from philo.models.fields import TemplateField
from philo.models.nodes import View
from philo.templatetags.containers import ContainerNode
from philo.utils import fattr
from philo.validators import LOADED_TEMPLATE_ATTR
from philo.signals import page_about_to_render_to_string, page_finished_rendering_to_string


class LazyContainerFinder(object):
	def __init__(self, nodes, extends=False):
		self.nodes = nodes
		self.initialized = False
		self.contentlet_specs = set()
		self.contentreference_specs = SortedDict()
		self.blocks = {}
		self.block_super = False
		self.extends = extends
	
	def process(self, nodelist):
		for node in nodelist:
			if self.extends:
				if isinstance(node, BlockNode):
					self.blocks[node.name] = block = LazyContainerFinder(node.nodelist)
					block.initialize()
					self.blocks.update(block.blocks)
				continue
			
			if isinstance(node, ContainerNode):
				if not node.references:
					self.contentlet_specs.add(node.name)
				else:
					if node.name not in self.contentreference_specs.keys():
						self.contentreference_specs[node.name] = node.references
				continue
			
			if isinstance(node, VariableNode):
				if node.filter_expression.var.lookups == (u'block', u'super'):
					self.block_super = True
			
			if hasattr(node, 'child_nodelists'):
				for nodelist_name in node.child_nodelists:
					if hasattr(node, nodelist_name):
						nodelist = getattr(node, nodelist_name)
						self.process(nodelist)
			
			# LOADED_TEMPLATE_ATTR contains the name of an attribute philo uses to declare a
			# node as rendering an additional template. Philo monkeypatches the attribute onto
			# the relevant default nodes and declares it on any native nodes.
			if hasattr(node, LOADED_TEMPLATE_ATTR):
				loaded_template = getattr(node, LOADED_TEMPLATE_ATTR)
				if loaded_template:
					nodelist = loaded_template.nodelist
					self.process(nodelist)
	
	def initialize(self):
		if not self.initialized:
			self.process(self.nodes)
			self.initialized = True


class Template(TreeModel):
	name = models.CharField(max_length=255)
	documentation = models.TextField(null=True, blank=True)
	mimetype = models.CharField(max_length=255, default=getattr(settings, 'DEFAULT_CONTENT_TYPE', 'text/html'))
	code = TemplateField(secure=False, verbose_name='django template code')
	
	@property
	def containers(self):
		"""
		Returns a tuple where the first item is a list of names of contentlets referenced by containers,
		and the second item is a list of tuples of names and contenttypes of contentreferences referenced by containers.
		This will break if there is a recursive extends or includes in the template code.
		Due to the use of an empty Context, any extends or include tags with dynamic arguments probably won't work.
		"""
		template = DjangoTemplate(self.code)
		
		def build_extension_tree(nodelist):
			nodelists = []
			extends = None
			for node in nodelist:
				if not isinstance(node, TextNode):
					if isinstance(node, ExtendsNode):
						extends = node
					break
			
			if extends:
				if extends.nodelist:
					nodelists.append(LazyContainerFinder(extends.nodelist, extends=True))
				loaded_template = getattr(extends, LOADED_TEMPLATE_ATTR)
				nodelists.extend(build_extension_tree(loaded_template.nodelist))
			else:
				# Base case: root.
				nodelists.append(LazyContainerFinder(nodelist))
			return nodelists
		
		# Build a tree of the templates we're using, placing the root template first.
		levels = build_extension_tree(template.nodelist)[::-1]
		
		contentlet_specs = set()
		contentreference_specs = SortedDict()
		blocks = {}
		
		for level in levels:
			level.initialize()
			contentlet_specs |= level.contentlet_specs
			contentreference_specs.update(level.contentreference_specs)
			for name, block in level.blocks.items():
				if block.block_super:
					blocks.setdefault(name, []).append(block)
				else:
					blocks[name] = [block]
		
		for block_list in blocks.values():
			for block in block_list:
				block.initialize()
				contentlet_specs |= block.contentlet_specs
				contentreference_specs.update(block.contentreference_specs)
		
		return contentlet_specs, contentreference_specs
	
	def __unicode__(self):
		return self.name
	
	class Meta:
		app_label = 'philo'


class Page(View):
	"""
	Represents a page - something which is rendered according to a template. The page will have a number of related Contentlets depending on the template selected - but these will appear only after the page has been saved with that template.
	"""
	template = models.ForeignKey(Template, related_name='pages')
	title = models.CharField(max_length=255)
	
	def get_containers(self):
		if not hasattr(self, '_containers'):
			self._containers = self.template.containers
		return self._containers
	containers = property(get_containers)
	
	def render_to_string(self, request=None, extra_context=None):
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
		return HttpResponse(self.render_to_string(request, extra_context), mimetype=self.template.mimetype)
	
	def __unicode__(self):
		return self.title
	
	def clean_fields(self, exclude=None):
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
	page = models.ForeignKey(Page, related_name='contentlets')
	name = models.CharField(max_length=255, db_index=True)
	content = TemplateField()
	
	def __unicode__(self):
		return self.name
	
	class Meta:
		app_label = 'philo'


class ContentReference(models.Model):
	page = models.ForeignKey(Page, related_name='contentreferences')
	name = models.CharField(max_length=255, db_index=True)
	content_type = models.ForeignKey(ContentType, verbose_name='Content type')
	content_id = models.PositiveIntegerField(verbose_name='Content ID', blank=True, null=True)
	content = generic.GenericForeignKey('content_type', 'content_id')
	
	def __unicode__(self):
		return self.name
	
	class Meta:
		app_label = 'philo'


register_templatetags('philo.templatetags.containers')


register_value_model(Template)
register_value_model(Page)