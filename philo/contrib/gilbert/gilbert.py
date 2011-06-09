from . import site
from django.contrib.auth.models import User, Group


site.register_model(User, icon_name='user')
site.register_model(Group, icon_name='users')