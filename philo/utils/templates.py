import itertools

from django.template import TextNode, VariableNode, Context
from django.template.loader_tags import BlockNode, ExtendsNode, BlockContext, ConstantIncludeNode
from django.utils.datastructures import SortedDict

from philo.templatetags.containers import ContainerNode


LOADED_TEMPLATE_ATTR = '_philo_loaded_template'
BLANK_CONTEXT = Context()


def get_extended(self):
	return self.get_parent(BLANK_CONTEXT)


def get_included(self):
	return self.template


# We ignore the IncludeNode because it will never work in a blank context.
setattr(ExtendsNode, LOADED_TEMPLATE_ATTR, property(get_extended))
setattr(ConstantIncludeNode, LOADED_TEMPLATE_ATTR, property(get_included))


def get_containers(template):
		# Build a tree of the templates we're using, placing the root template first.
		levels = build_extension_tree(template.nodelist)
		
		contentlet_specs = []
		contentreference_specs = SortedDict()
		blocks = {}
		
		for level in reversed(levels):
			level.initialize()
			contentlet_specs.extend(itertools.ifilter(lambda x: x not in contentlet_specs, level.contentlet_specs))
			contentreference_specs.update(level.contentreference_specs)
			for name, block in level.blocks.items():
				if block.block_super:
					blocks.setdefault(name, []).append(block)
				else:
					blocks[name] = [block]
		
		for block_list in blocks.values():
			for block in block_list:
				block.initialize()
				contentlet_specs.extend(itertools.ifilter(lambda x: x not in contentlet_specs, block.contentlet_specs))
				contentreference_specs.update(block.contentreference_specs)
		
		return contentlet_specs, contentreference_specs


class LazyContainerFinder(object):
	def __init__(self, nodes, extends=False):
		self.nodes = nodes
		self.initialized = False
		self.contentlet_specs = []
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
					self.contentlet_specs.append(node.name)
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