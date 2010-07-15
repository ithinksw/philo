from django import template
from django.conf import settings
from django.contrib.sites.models import Site


register = template.Library()


class NodeURLNode(template.Node):
	def __init__(self, node, with_obj, as_var):
		if node is not None:
			self.node = template.Variable(node)
		else:
			self.node = None
		
		if with_obj is not None:
			self.with_obj = template.Variable(with_obj)
		else:
			self.with_obj = None
		
		self.as_var = as_var
	
	def render(self, context):
		try:
			if self.node:
				node = self.node.resolve(context)
			else:
				node = context['node']
			current_site = Site.objects.get_current()
			if node.has_ancestor(current_site.root_node):
				url = node.get_path(root=current_site.root_node)
				if self.with_obj:
					with_obj = self.with_obj.resolve(context)
					url += node.view.get_subpath(with_obj)
			else:
				return settings.TEMPLATE_STRING_IF_INVALID
			
			if self.as_var:
				context[self.as_var] = url
				return settings.TEMPLATE_STRING_IF_INVALID
			else:
				return url
		except:
			return settings.TEMPLATE_STRING_IF_INVALID


@register.tag(name='node_url')
def do_node_url(parser, token):
	"""
	{% node_url [<node>] [with <obj>] [as <var>] %}
	"""
	params = token.split_contents()
	tag = params[0]
	
	if len(params) <= 6:
		node = None
		with_obj = None
		as_var = None
		remaining_tokens = params[1:]
		while remaining_tokens:
			option_token = remaining_tokens.pop(0)
			if option_token == 'with':
				try:
					with_obj = remaining_tokens.pop(0)
				except IndexError:
					raise template.TemplateSyntaxError('"%s" template tag option "with" requires an argument specifying an object handled by the view on the node' % tag)
			elif option_token == 'as':
				try:
					as_var = remaining_tokens.pop(0)
				except IndexError:
					raise template.TemplateSyntaxError('"%s" template tag option "as" requires an argument specifying a variable name' % tag)
			else: # node
				node = option_token
		return NodeURLNode(node=node, with_obj=with_obj, as_var=as_var)
	else:
		raise template.TemplateSyntaxError('"%s" template tag cannot accept more than five arguments' % tag)