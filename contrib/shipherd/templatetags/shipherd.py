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
		
		# loosely based on django.template.defaulttags.ForNode.render
		children = item.get_children()
		parentloop = context['navloop']
		loop_dict = context['navloop'] = {'parentloop':parentloop}
		len_items = len(children)
		for i, child in enumerate(children):
			context['item'] = child
			loop_dict['counter0'] = i
			loop_dict['counter'] = i + 1
			loop_dict['revcounter'] = len_items - i
			loop_dict['revcounter0'] = len_items - i - 1
			loop_dict['first'] = (i == 0)
			loop_dict['last'] = (i == len_items - 1)
			bits.append(self._render_node(context, child, request))
		context['navloop'] = context['navloop']['parentloop']
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
			items = instance.navigation[self.key]
		except:
			return settings.TEMPLATE_STRING_IF_INVALID
		
		bits = []
		
		# loosely based on django.template.defaulttags.ForNode.render
		# This is a repetition of the stuff that happens above. We should eliminate that somehow.
		loop_dict = context['navloop'] = {'parentloop':{}}
		len_items = len(items)
		for i, item in enumerate(items):
			loop_dict['counter0'] = i
			loop_dict['counter'] = i + 1
			loop_dict['revcounter'] = len_items - i
			loop_dict['revcounter0'] = len_items - i - 1
			loop_dict['first'] = (i == 0)
			loop_dict['last'] = (i == len_items - 1)
			bits.append(self._render_node(context, item, request))
		
		return ''.join(bits)


@register.tag
def recursenavigation(parser, token):
	"""
	Based on django-mptt's recursetree templatetag. In addition to {{ item }} and {{ children }},
	sets {{ active }}, {{ active_descendants }}, {{ navloop.counter }}, {{ navloop.counter0 }},
	{{ navloop.revcounter }}, {{ navloop.revcounter0 }}, {{ navloop.first }}, {{ navloop.last }},
	and {{ navloop.parentloop }} in the context.
	
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
def has_navigation(node, key=None):
	try:
		nav = node.navigation
		if key is not None:
			if key in nav and bool(node.navigation[key]):
				return True
			elif key not in node.navigation:
				return False
		return bool(node.navigation)
	except:
		return False


@register.filter
def navigation_host(node, key):
	try:
		return Navigation.objects.filter(node__in=node.get_ancestors(include_self=True), key=key).order_by('-node__level')[0].node
	except:
		if settings.TEMPLATE_DEBUG:
			raise
		return node