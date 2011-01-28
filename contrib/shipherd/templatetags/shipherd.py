from django import template
from django.conf import settings
from django.utils.safestring import mark_safe
from philo.contrib.shipherd.models import Navigation
from philo.models import Node
from mptt.templatetags.mptt_tags import RecurseTreeNode, cache_tree_children
from django.utils.translation import ugettext as _


register = template.Library()


class RecurseNavigationNode(RecurseTreeNode):
	def __init__(self, template_nodes, instance_var, key):
		self.template_nodes = template_nodes
		self.instance_var = instance_var
		self.key = key
	
	def _render_node(self, context, item, request):
		bits = []
		context.push()
		for child in item.get_children():
			context['item'] = child
			bits.append(self._render_node(context, child, request))
		context['item'] = item
		context['children'] = mark_safe(u''.join(bits))
		context['active'] = item.is_active(request)
		context['active_descendants'] = item.has_active_descendants(request)
		rendered = self.template_nodes.render(context)
		context.pop()
		return rendered
	
	def render(self, context):
		try:
			request = context['request']
		except KeyError:
			return ''
		
		instance = self.instance_var.resolve(context)
		
		try:
			navigation = instance.navigation[self.key]
		except:
			return settings.TEMPLATE_STRING_IF_INVALID
		
		bits = [self._render_node(context, item, request) for item in navigation]
		return ''.join(bits)


@register.tag
def recursenavigation(parser, token):
	"""
	Based on django-mptt's recursetree templatetag. In addition to {{ item }} and {{ children }},
	sets {{ active }} and {{ active_descendants }} in the context.
	
	Note that the tag takes one variable, which is a Node instance.
	
	Usage:
		<ul>
			{% recursenavigation node main %}
				<li{% if active %} class='active'{% endif %}>
					{{ navigation.text }}
					{% if navigation.get_children %}
						<ul>
							{{ children }}
						</ul>
					{% endif %}
				</li>
			{% endrecursenavigation %}
		</ul>
	"""
	bits = token.contents.split()
	if len(bits) != 3:
		raise template.TemplateSyntaxError(_('%s tag requires two arguments: a node and a navigation section name') % bits[0])
	
	instance_var = parser.compile_filter(bits[1])
	key = bits[2]
	
	template_nodes = parser.parse(('endrecursenavigation',))
	parser.delete_first_token()
	
	return RecurseNavigationNode(template_nodes, instance_var, key)


@register.filter
def has_navigation(node): # optional arg for a key?
	return bool(node.navigation)


@register.filter
def navigation_host(node, key):
	try:
		return Navigation.objects.filter(node__in=node.get_ancestors(include_self=True), key=key).order_by('-node__level')[0].node
	except:
		if settings.TEMPLATE_DEBUG:
			raise
		return node