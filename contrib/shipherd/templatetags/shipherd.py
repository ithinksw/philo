from django import template
from django.conf import settings
from django.utils.safestring import mark_safe
from philo.contrib.shipherd.models import Navigation
from mptt.templatetags.mptt_tags import RecurseTreeNode, cache_tree_children


register = template.Library()


class RecurseNavigationNode(RecurseTreeNode):
	def __init__(self, template_nodes, instance_var):
		self.template_nodes = template_nodes
		self.instance_var = instance_var
	
	def _render_node(self, context, node, request):
		bits = []
		context.push()
		for child in node.get_children():
			context['navigation'] = child
			bits.append(self._render_node(context, child, request))
		context['navigation'] = node
		context['children'] = mark_safe(u''.join(bits))
		context['active'] = node.is_active(request)
		rendered = self.template_nodes.render(context)
		context.pop()
		return rendered
	
	def render(self, context):
		try:
			request = context['request']
		except KeyError:
			return ''
		
		instance = self.instance_var.resolve(context)
		roots = cache_tree_children(Navigation.objects.closest_navigation(instance))
		bits = [self._render_node(context, node, request) for node in roots]
		return ''.join(bits)


@register.tag
def recursenavigation(parser, token):
	"""
	Based on django-mptt's recursetree templatetag. In addition to {{ navigation }} and {{ children }},
	sets {{ active }} in the context.
	
	Note that the tag takes one variable, which is a Node instance.
	
	Usage:
		<ul>
			{% recursenavigation node %}
				<li{% if active %} class='active'{% endif %}>
					{{ navigation.text }}
					{% if not navigation.is_leaf_node %}
						<ul>
							{{ children }}
						</ul>
					{% endif %}
				</li>
			{% endrecursenavigation %}
		</ul>
	"""
	bits = token.contents.split()
	if len(bits) != 2:
		raise template.TemplateSyntaxError(_('%s tag requires an instance') % bits[0])
	
	instance_var = template.Variable(bits[1])
	
	template_nodes = parser.parse(('endrecursenavigation',))
	parser.delete_first_token()
	
	return RecurseNavigationNode(template_nodes, instance_var)


@register.filter
def has_navigation(node):
	return bool(Navigation.objects.closest_navigation(node).count())