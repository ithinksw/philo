from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import validate_slug
from django.db import models
from django.utils import simplejson as json
from django.utils.text import capfirst
from django.utils.translation import ugettext_lazy as _

from philo.forms.fields import JSONFormField
from philo.utils.registry import RegistryIterator
from philo.validators import TemplateValidator, json_validator
#from philo.models.fields.entities import *


class TemplateField(models.TextField):
	"""A :class:`TextField` which is validated with a :class:`.TemplateValidator`. ``allow``, ``disallow``, and ``secure`` will be passed into the validator's construction."""
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
	"""A :class:`TextField` which stores its value on the model instance as a python object and stores its value in the database as JSON. Validated with :func:`.json_validator`."""
	default_validators = [json_validator]
	
	def get_attname(self):
		return "%s_json" % self.name
	
	def contribute_to_class(self, cls, name):
		super(JSONField, self).contribute_to_class(cls, name)
		setattr(cls, name, JSONDescriptor(self))
		models.signals.pre_init.connect(self.fix_init_kwarg, sender=cls)
	
	def fix_init_kwarg(self, sender, args, kwargs, **signal_kwargs):
		# Anything passed in as self.name is assumed to come from a serializer and
		# will be treated as a json string.
		if self.name in kwargs:
			value = kwargs.pop(self.name)
			
			# Hack to handle the xml serializer's handling of "null"
			if value is None:
				value = 'null'
			
			kwargs[self.attname] = value
	
	def formfield(self, *args, **kwargs):
		kwargs["form_class"] = JSONFormField
		return super(JSONField, self).formfield(*args, **kwargs)


class SlugMultipleChoiceField(models.Field):
	"""Stores a selection of multiple items with unique slugs in the form of a comma-separated list. Also knows how to correctly handle :class:`RegistryIterator`\ s passed in as choices."""
	__metaclass__ = models.SubfieldBase
	description = _("Comma-separated slug field")
	
	def get_internal_type(self):
		return "TextField"
	
	def to_python(self, value):
		if not value:
			return []
		
		if isinstance(value, list):
			return value
		
		return value.split(',')
	
	def get_prep_value(self, value):
		return ','.join(value)
	
	def formfield(self, **kwargs):
		# This is necessary because django hard-codes TypedChoiceField for things with choices.
		defaults = {
			'widget': forms.CheckboxSelectMultiple,
			'choices': self.get_choices(include_blank=False),
			'label': capfirst(self.verbose_name),
			'required': not self.blank,
			'help_text': self.help_text
		}
		if self.has_default():
			if callable(self.default):
				defaults['initial'] = self.default
				defaults['show_hidden_initial'] = True
			else:
				defaults['initial'] = self.get_default()
		
		for k in kwargs.keys():
			if k not in ('coerce', 'empty_value', 'choices', 'required',
						 'widget', 'label', 'initial', 'help_text',
						 'error_messages', 'show_hidden_initial'):
				del kwargs[k]
		
		defaults.update(kwargs)
		form_class = forms.TypedMultipleChoiceField
		return form_class(**defaults)
	
	def validate(self, value, model_instance):
		invalid_values = []
		for val in value:
			try:
				validate_slug(val)
			except ValidationError:
				invalid_values.append(val)
		
		if invalid_values:
			# should really make a custom message.
			raise ValidationError(self.error_messages['invalid_choice'] % invalid_values)
	
	def _get_choices(self):
		if isinstance(self._choices, RegistryIterator):
			return self._choices.copy()
		elif hasattr(self._choices, 'next'):
			choices, self._choices = itertools.tee(self._choices)
			return choices
		else:
			return self._choices
	choices = property(_get_choices)


try:
	from south.modelsinspector import add_introspection_rules
except ImportError:
	pass
else:
	add_introspection_rules([], ["^philo\.models\.fields\.SlugMultipleChoiceField"])
	add_introspection_rules([], ["^philo\.models\.fields\.TemplateField"])
	add_introspection_rules([], ["^philo\.models\.fields\.JSONField"])