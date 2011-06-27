from django import template, VERSION as django_version
from django.conf import settings
from django.utils.safestring import mark_safe
from philo.contrib.shipherd.models import Navigation
from philo.models import Node
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext as _


register = template.Library()


class LazyNavigationRecurser(object):
	def __init__(self, template_nodes, items, context, request):
		self.template_nodes = template_nodes
		self.items = items
		self.context = context
		self.request = request
	
	def __call__(self):
		items = self.items
		context = self.context
		request = self.request
		
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
			loop_dict['active'] = context['active'] = item.is_active(request)
			loop_dict['active_descendants'] = context['active_descendants'] = item.has_active_descendants(request)
			
			# Set these directly in the context for easy access.
			context['item'] = item
			context['children'] = self.__class__(self.template_nodes, item.get_children(), context, request)
			
			# Then render the nodelist bit by bit.
			for node in self.template_nodes:
				bits.append(node.render(context))
		context.pop()
		return mark_safe(''.join(bits))


class RecurseNavigationNode(template.Node):
	def __init__(self, template_nodes, instance_var, key_var):
		self.template_nodes = template_nodes
		self.instance_var = instance_var
		self.key_var = key_var
	
	def render(self, context):
		try:
			request = context['request']
		except KeyError:
			return ''
		
		instance = self.instance_var.resolve(context)
		key = self.key_var.resolve(context)
		
		# Fall back on old behavior if the key doesn't seem to be a variable.
		if not key:
			token = self.key_var.token
			if token[0] not in ["'", '"'] and '.' not in token:
				key = token
			else:
				return settings.TEMPLATE_STRING_IF_INVALID
		
		try:
			items = instance.navigation[key]
		except:
			return settings.TEMPLATE_STRING_IF_INVALID
		
		return LazyNavigationRecurser(self.template_nodes, items, context, request)()


@register.tag
def recursenavigation(parser, token):
	"""
	The :ttag:`recursenavigation` templatetag takes two arguments:
	
	* the :class:`.Node` for which the :class:`.Navigation` should be found
	* the :class:`.Navigation`'s :attr:`~.Navigation.key`.
	
	It will then recursively loop over each :class:`.NavigationItem` in the :class:`.Navigation` and render the template
	chunk within the block. :ttag:`recursenavigation` sets the following variables in the context:
	
		==============================  ================================================
		Variable                        Description
		==============================  ================================================
		``navloop.depth``               The current depth of the loop (1 is the top level)
		``navloop.depth0``              The current depth of the loop (0 is the top level)
		``navloop.counter``             The current iteration of the current level(1-indexed)
		``navloop.counter0``            The current iteration of the current level(0-indexed)
		``navloop.first``               True if this is the first time through the current level
		``navloop.last``                True if this is the last time through the current level
		``navloop.parentloop``          This is the loop one level "above" the current one
		
		``item``                        The current item in the loop (a :class:`.NavigationItem` instance)
		``children``                    If accessed, performs the next level of recursion.
		``navloop.active``              True if the item is active for this request
		``navloop.active_descendants``  True if the item has active descendants for this request
		==============================  ================================================
	
	Example::
	
		<ul>
		    {% recursenavigation node "main" %}
		        <li{% if navloop.active %} class='active'{% endif %}>
		            <a href="{{ item.get_target_url }}">{{ item.text }}</a>
		            {% if item.get_children %}
		                <ul>
		                    {{ children }}
		                </ul>
		            {% endif %}
		        </li>
		    {% endrecursenavigation %}
		</ul>
	
	.. note:: {% recursenavigation %} requires that the current :class:`HttpRequest` be present in the context as ``request``. The simplest way to do this is with the `request context processor`_. Simply make sure that ``django.core.context_processors.request`` is included in your :setting:`TEMPLATE_CONTEXT_PROCESSORS` setting.
	
	.. _request context processor: https://docs.djangoproject.com/en/dev/ref/templates/api/#django-core-context-processors-request
	
	"""
	bits = token.contents.split()
	if len(bits) != 3:
		raise template.TemplateSyntaxError(_('%s tag requires two arguments: a node and a navigation section name') % bits[0])
	
	instance_var = parser.compile_filter(bits[1])
	key_var = parser.compile_filter(bits[2])
	
	template_nodes = parser.parse(('endrecursenavigation',))
	token = parser.delete_first_token()
	return RecurseNavigationNode(template_nodes, instance_var, key_var)


@register.filter
def has_navigation(node, key=None):
	"""Returns ``True`` if the node has a :class:`.Navigation` with the given key and ``False`` otherwise. If ``key`` is ``None``, returns whether the node has any :class:`.Navigation`\ s at all."""
	try:
		return bool(node.navigation[key])
	except:
		return False


@register.filter
def navigation_host(node, key):
	"""Returns the :class:`.Node` which hosts the :class:`.Navigation` which ``node`` has inherited for ``key``. Returns ``node`` if any exceptions are encountered."""
	try:
		return node.navigation[key].node
	except:
		return node