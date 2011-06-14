from django.db import models
from django.contrib.auth.models import User
from philo.models.fields import JSONField


class UserPreferences(models.Model):
	user = models.OneToOneField(User, related_name='gilbert_userpreferences')
	preferences = JSONField(default=dict())