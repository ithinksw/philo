from django import template
from django.conf import settings
from philo.contrib.navigation.models import Navigation


register = template.Library()


@register.filter
def get_navigation(node):
	roots = Navigation.objects.for_node(node)
	qs = None
	for root in roots:
		root_qs = root.get_descendants(include_self=True).complex_filter({'%s__lte' % root._mptt_meta.level_attr: root.get_level() + root.depth}).exclude(depth__isnull=True)
		if qs is None:
			qs = root_qs
		else:
			qs |= root_qs
	return qs

@register.filter
def is_active(navigation, request):
	"""
	Returns true if the navigation is considered `active`.
	
	But what does "active" mean? Should this be defined on the model instead, perhaps?
	"""
	try:
		if navigation.target_node == request.node:
			if request.path == navigation.target_url:
				return True
			return False
		if navigation.target_url in request.path:
			return True
	except:
		pass
	return False