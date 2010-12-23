from django import template
from django.conf import settings
from philo.contrib.navigation.models import Navigation


register = template.Library()


@register.filter
def get_navigation(node):
	return Navigation.objects.closest_navigation(node)

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