from philo.models.base import *
from philo.models.collections import *
from philo.models.nodes import *
from philo.models.pages import *
from django.contrib.auth.models import User, Group
from django.contrib.sites.models import Site


register_value_model(User)
register_value_model(Group)
register_value_model(Site)
register_templatetags('philo.templatetags.embed')