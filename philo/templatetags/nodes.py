"""
The node template tags are automatically included as builtins if :mod:`philo` is an installed app.

"""

from django import template
from django.conf import settings
from django.contrib.sites.models import Site
from django.core.urlresolvers import reverse, NoReverseMatch
from django.template.defaulttags import kwarg_re
from django.utils.encoding import smart_str

from philo.exceptions import ViewCanNotProvideSubpath


register = template.Library()


class NodeURLNode(template.Node):
	def __init__(self, node, as_var, with_obj=None, view_name=None, args=None, kwargs=None):
		self.as_var = as_var
		self.view_name = view_name
		
		# Because the following variables have already been compiled as filters if they exist, they don't need to be re-scanned as template variables.
		self.node = node
		self.with_obj = with_obj
		self.args = args
		self.kwargs = kwargs
	
	def render(self, context):
		if self.node:
			node = self.node.resolve(context)
		else:
			node = context.get('node', None)
		
		if not node:
			return settings.TEMPLATE_STRING_IF_INVALID
		
		if self.with_obj is None and self.view_name is None:
			url = node.get_absolute_url()
		else:
			if not node.accepts_subpath:
				return settings.TEMPLATE_STRING_IF_INVALID
			
			if self.with_obj is not None:
				try:
					view_name, args, kwargs = node.view.get_reverse_params(self.with_obj.resolve(context))
				except ViewCanNotProvideSubpath:
					return settings.TEMPLATE_STRING_IF_INVALID
			else: # self.view_name is not None
				view_name = self.view_name
				args = [arg.resolve(context) for arg in self.args]
				kwargs = dict([(smart_str(k, 'ascii'), v.resolve(context)) for k, v in self.kwargs.items()])
			
			url = ''
			try:
				subpath = reverse(view_name, urlconf=node.view, args=args, kwargs=kwargs)
			except NoReverseMatch:
				if self.as_var is None:
					if settings.TEMPLATE_DEBUG:
						raise
					return settings.TEMPLATE_STRING_IF_INVALID
			else:
				url = node.construct_url(subpath)
		
		if self.as_var:
			context[self.as_var] = url
			return ''
		else:
			return url


@register.tag
def node_url(parser, token):
	"""
	The :ttag:`node_url` tag allows access to :meth:`.View.reverse` from a template for a :class:`.Node`. By default, the :class:`.Node` that is used for the call is pulled from the context variable ``node``; however, this can be overridden with the ``[for <node>]`` option.
	
	Usage::
	
		{% node_url [for <node>] [as <var>] %}
		{% node_url with <obj> [for <node>] [as <var>] %}
		{% node_url <view_name> [<arg1> [<arg2> ...] ] [for <node>] [as <var>] %}
		{% node_url <view_name> [<key1>=<value1> [<key2>=<value2> ...] ] [for <node>] [as <var>] %}
	
	"""
	params = token.split_contents()
	tag = params[0]
	as_var = None
	with_obj = None
	node = None
	params = params[1:]
	
	if len(params) >= 2 and params[-2] == 'as':
		as_var = params[-1]
		params = params[:-2]
	
	if len(params) >= 2 and params[-2] == 'for':
		node = parser.compile_filter(params[-1])
		params = params[:-2]
	
	if len(params) >= 2 and params[-2] == 'with':
		with_obj = parser.compile_filter(params[-1])
		params = params[:-2]
	
	if with_obj is not None:
		if params:
			raise template.TemplateSyntaxError('`%s` template tag accepts no arguments or keyword arguments if with <obj> is specified.' % tag)
		return NodeURLNode(with_obj=with_obj, node=node, as_var=as_var)
	
	if params:
		args = []
		kwargs = {}
		view_name = params.pop(0)
		for param in params:
			match = kwarg_re.match(param)
			if not match:
				raise TemplateSyntaxError("Malformed arguments to `%s` tag" % tag)
			name, value = match.groups()
			if name:
				kwargs[name] = parser.compile_filter(value)
			else:
				args.append(parser.compile_filter(value))
		return NodeURLNode(view_name=view_name, args=args, kwargs=kwargs, node=node, as_var=as_var)
	
	return NodeURLNode(node=node, as_var=as_var)