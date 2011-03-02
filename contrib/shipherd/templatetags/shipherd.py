from django import template
from django.conf import settings
from django.utils.safestring import mark_safe
from philo.contrib.shipherd.models import Navigation
from philo.models import Node
from django.utils.translation import ugettext as _


register = template.Library()


class RecurseNavigationMarker(object):
	pass


class RecurseNavigationNode(template.Node):
	def __init__(self, template_nodes, instance_var, key):
		self.template_nodes = template_nodes
		self.instance_var = instance_var
		self.key = key
	
	def _render_items(self, items, context, request):
		if not items:
			return ''
		
		if 'navloop' in context:
			parentloop = context['navloop']
		else:
			parentloop = {}
		context.push()
		
		depth = items[0].get_level()
		len_items = len(items)
		
		loop_dict = context['navloop'] = {
			'parentloop': parentloop,
			'depth': depth + 1,
			'depth0': depth
		}
		
		bits = []
		
		for i, item in enumerate(items):
			# First set context variables.
			loop_dict['counter0'] = i
			loop_dict['counter'] = i + 1
			loop_dict['revcounter'] = len_items - i
			loop_dict['revcounter0'] = len_items - i - 1
			loop_dict['first'] = (i == 0)
			loop_dict['last'] = (i == len_items - 1)
			
			# Set on loop_dict and context for backwards-compatibility.
			# Eventually only allow access through the loop_dict.
			loop_dict['item'] = context['item'] = item
			loop_dict['active'] = context['active'] = item.is_active(request)
			loop_dict['active_descendants'] = context['active_descendants'] = item.has_active_descendants(request)
			
			# Then render the nodelist bit by bit.
			for node in self.template_nodes:
				if isinstance(node, RecurseNavigationMarker):
					# Then recurse!
					children = items.get_children()
					bits.append(self._render_items(children, context, request))
				elif isinstance(node, template.VariableNode) and node.filter_expression.var.lookups == (u'children',):
					# Then recurse! This is here for backwards-compatibility only.
					children = items.get_children()
					bits.append(self._render_items(children, context, request))
				else:
					bits.append(node.render(context))
		context.pop()
		return ''.join(bits)
	
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
		
		return self._render_items(items, context, request)


@register.tag
def recursenavigation(parser, token):
	"""
	Based on django-mptt's recursetree templatetag. In addition to {{ item }} and {{ children }},
	sets {{ active }}, {{ active_descendants }}, {{ navloop.counter }}, {{ navloop.counter0 }},
	{{ navloop.revcounter }}, {{ navloop.revcounter0 }}, {{ navloop.first }}, {{ navloop.last }},
	and {{ navloop.parentloop }} in the context.
	
	Note that the tag takes two variables: a Node instance and the key of the navigation to
	be recursed.
	
	Usage:
		<ul>
			{% recursenavigation node main %}
				<li{% if active %} class='active'{% endif %}>
					{{ item.text }}
					{% if item.get_children %}
						<ul>
							{% recurse %}
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
	
	template_nodes = parser.parse(('recurse', 'endrecursenavigation',))
	
	token = parser.next_token()
	if token.contents == 'recurse':
		template_nodes.append(RecurseNavigationMarker())
		template_nodes.extend(parser.parse(('endrecursenavigation')))
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