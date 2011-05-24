from django import forms
from django.core.exceptions import ValidationError
from django.utils import simplejson as json

from philo.validators import json_validator


__all__ = ('JSONFormField',)


class JSONFormField(forms.Field):
	"""A form field which is validated by :func:`philo.validators.json_validator`."""
	default_validators = [json_validator]
	
	def clean(self, value):
		if value == '' and not self.required:
			return None
		try:
			return json.loads(value)
		except Exception, e:
			raise ValidationError(u'JSON decode error: %s' % e)