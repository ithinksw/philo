from django.conf import settings
from django.contrib.auth.models import User, Group
from django.contrib.sites.models import Site

from philo.models.base import *
from philo.models.collections import *
from philo.models.nodes import *
from philo.models.pages import *


register_value_model(User)
register_value_model(Group)
register_value_model(Site)

if 'philo' in settings.INSTALLED_APPS:
	from django.template import add_to_builtins
	add_to_builtins('philo.templatetags.embed')
	add_to_builtins('philo.templatetags.containers')
	add_to_builtins('philo.templatetags.collections')
	add_to_builtins('philo.templatetags.nodes')