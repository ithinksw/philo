from django.contrib.localflavor.us.forms import USZipCodeField as USZipCodeFormField
from django.core.validators import RegexValidator
from django.db import models


class USZipCodeField(models.CharField):
	default_validators = [RegexValidator(r'^\d{5}(?:-\d{4})?$')]
	
	def __init__(self, *args, **kwargs):
		kwargs['max_length'] = 10
		super(USZipCodeField, self).__init__(*args, **kwargs)
	
	def formfield(self, form_class=USZipCodeFormField, **kwargs):
		return super(USZipCodeField, self).formfield(form_class, **kwargs)


try:
	from south.modelsinspector import add_introspection_rules
except ImportError:
	pass
else:
	add_introspection_rules([], ["^philo\.contrib\.julian\.fields\.USZipCodeField"])