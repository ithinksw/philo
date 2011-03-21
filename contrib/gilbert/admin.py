from django.contrib.admin import site
from .models import UserPreferences

site.register(UserPreferences)