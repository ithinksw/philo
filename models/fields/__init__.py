from django import forms
from django.db import models
from django.utils import simplejson as json
from philo.forms.fields import JSONFormField
from philo.validators import TemplateValidator, json_validator
#from philo.models.fields.entities import *


class TemplateField(models.TextField):
	def __init__(self, allow=None, disallow=None, secure=True, *args, **kwargs):
		super(TemplateField, self).__init__(*args, **kwargs)
		self.validators.append(TemplateValidator(allow, disallow, secure))


class JSONDescriptor(object):
	def __init__(self, field):
		self.field = field
	
	def __get__(self, instance, owner):
		if instance is None:
			raise AttributeError # ?
		
		if self.field.name not in instance.__dict__:
			json_string = getattr(instance, self.field.attname)
			instance.__dict__[self.field.name] = json.loads(json_string)
		
		return instance.__dict__[self.field.name]
	
	def __set__(self, instance, value):
		instance.__dict__[self.field.name] = value
		setattr(instance, self.field.attname, json.dumps(value))
	
	def __delete__(self, instance):
		del(instance.__dict__[self.field.name])
		setattr(instance, self.field.attname, json.dumps(None))


class JSONField(models.TextField):
	default_validators = [json_validator]
	
	def get_attname(self):
		return "%s_json" % self.name
	
	def contribute_to_class(self, cls, name):
		super(JSONField, self).contribute_to_class(cls, name)
		setattr(cls, name, JSONDescriptor(self))
		models.signals.pre_init.connect(self.fix_init_kwarg, sender=cls)
	
	def fix_init_kwarg(self, sender, args, kwargs, **signal_kwargs):
		if self.name in kwargs:
			kwargs[self.attname] = json.dumps(kwargs.pop(self.name))
	
	def formfield(self, *args, **kwargs):
		kwargs["form_class"] = JSONFormField
		return super(JSONField, self).formfield(*args, **kwargs)


try:
	from south.modelsinspector import add_introspection_rules
except ImportError:
	pass
else:
	add_introspection_rules([], ["^philo\.models\.fields\.TemplateField"])
	add_introspection_rules([], ["^philo\.models\.fields\.JSONField"])