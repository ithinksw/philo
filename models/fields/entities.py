"""
The EntityProxyFields defined in this file can be assigned as fields on
a subclass of philo.models.Entity. They act like any other model
fields, but instead of saving their data to the database, they save it
to attributes related to a model instance. Additionally, a new
attribute will be created for an instance if and only if the field's
value has been set. This is relevant i.e. for passthroughs, where the
value of the field may be defined by some other instance's attributes.

Example::

	class Thing(Entity):
		numbers = models.PositiveIntegerField()
	
	class ThingProxy(Thing):
		improvised = JSONAttribute(models.BooleanField)
"""
from itertools import tee
from django import forms
from django.core.exceptions import FieldError
from django.db import models
from django.db.models.fields import NOT_PROVIDED
from django.utils.text import capfirst
from philo.signals import entity_class_prepared
from philo.models import ManyToManyValue, JSONValue, ForeignKeyValue, Attribute, Entity
import datetime


__all__ = ('JSONAttribute', 'ForeignKeyAttribute', 'ManyToManyAttribute')


ATTRIBUTE_REGISTRY = '_attribute_registry'


class EntityProxyField(object):
	def __init__(self, verbose_name=None, help_text=None, default=NOT_PROVIDED, editable=True, choices=None, *args, **kwargs):
		self.verbose_name = verbose_name
		self.help_text = help_text
		self.default = default
		self.editable = editable
		self._choices = choices or []
	
	def actually_contribute_to_class(self, sender, **kwargs):
		sender._entity_meta.add_proxy_field(self)
	
	def contribute_to_class(self, cls, name):
		if issubclass(cls, Entity):
			self.name = self.attname = name
			self.model = cls
			if self.verbose_name is None and name:
				self.verbose_name = name.replace('_', ' ')
			entity_class_prepared.connect(self.actually_contribute_to_class, sender=cls)
		else:
			raise FieldError('%s instances can only be declared on Entity subclasses.' % self.__class__.__name__)
	
	def formfield(self, form_class=forms.CharField, **kwargs):
		defaults = {
			'required': False,
			'label': capfirst(self.verbose_name),
			'help_text': self.help_text
		}
		if self.has_default():
			defaults['initial'] = self.default
		defaults.update(kwargs)
		return form_class(**defaults)
	
	def value_from_object(self, obj):
		"""The return value of this method will be used by the EntityForm as
		this field's initial value."""
		return getattr(obj, self.name)
	
	def get_storage_value(self, value):
		"""Final conversion of `value` before it gets stored on an Entity instance.
		This step is performed by the ProxyFieldForm."""
		return value
	
	def has_default(self):
		return self.default is not NOT_PROVIDED
	
	def _get_choices(self):
		if hasattr(self._choices, 'next'):
			choices, self._choices = tee(self._choices)
			return choices
		else:
			return self._choices
	choices = property(_get_choices)


class AttributeFieldDescriptor(object):
	def __init__(self, field):
		self.field = field
	
	def get_registry(self, instance):
		if ATTRIBUTE_REGISTRY not in instance.__dict__:
			instance.__dict__[ATTRIBUTE_REGISTRY] = {'added': set(), 'removed': set()}
		return instance.__dict__[ATTRIBUTE_REGISTRY]
	
	def __get__(self, instance, owner):
		if instance is None:
			return self
		
		if self.field.name not in instance.__dict__:
			instance.__dict__[self.field.name] = instance.attributes.get(self.field.attribute_key, None)
		
		return instance.__dict__[self.field.name]
	
	def __set__(self, instance, value):
		if instance is None:
			raise AttributeError("%s must be accessed via instance" % self.field.name)
		
		self.field.validate_value(value)
		instance.__dict__[self.field.name] = value
		
		registry = self.get_registry(instance)
		registry['added'].add(self.field)
		registry['removed'].discard(self.field)
	
	def __delete__(self, instance):
		del instance.__dict__[self.field.name]
		
		registry = self.get_registry(instance)
		registry['added'].discard(self.field)
		registry['removed'].add(self.field)


def process_attribute_fields(sender, instance, created, **kwargs):
	if ATTRIBUTE_REGISTRY in instance.__dict__:
		registry = instance.__dict__[ATTRIBUTE_REGISTRY]
		instance.attribute_set.filter(key__in=[field.attribute_key for field in registry['removed']]).delete()
		
		for field in registry['added']:
			try:
				attribute = instance.attribute_set.get(key=field.attribute_key)
			except Attribute.DoesNotExist:
				attribute = Attribute()
				attribute.entity = instance
				attribute.key = field.attribute_key
			
			value_class = field.value_class
			if isinstance(attribute.value, value_class):
				value = attribute.value
			else:
				if isinstance(attribute.value, models.Model):
					attribute.value.delete()
				value = value_class()
			
			value.set_value(getattr(instance, field.name, None))
			value.save()
			
			attribute.value = value
			attribute.save()
		del instance.__dict__[ATTRIBUTE_REGISTRY]


class AttributeField(EntityProxyField):
	def __init__(self, attribute_key=None, **kwargs):
		self.attribute_key = attribute_key
		super(AttributeField, self).__init__(**kwargs)
	
	def actually_contribute_to_class(self, sender, **kwargs):
		super(AttributeField, self).actually_contribute_to_class(sender, **kwargs)
		setattr(sender, self.name, AttributeFieldDescriptor(self))
		opts = sender._entity_meta
		if not hasattr(opts, '_has_attribute_fields'):
			opts._has_attribute_fields = True
			models.signals.post_save.connect(process_attribute_fields, sender=sender)
	
	def contribute_to_class(self, cls, name):
		if self.attribute_key is None:
			self.attribute_key = name
		super(AttributeField, self).contribute_to_class(cls, name)
	
	def validate_value(self, value):
		"Confirm that the value is valid or raise an appropriate error."
		pass
	
	@property
	def value_class(self):
		raise AttributeError("value_class must be defined on AttributeField subclasses.")


class JSONAttribute(AttributeField):
	value_class = JSONValue
	
	def __init__(self, field_template=None, **kwargs):
		super(JSONAttribute, self).__init__(**kwargs)
		if field_template is None:
			field_template = models.CharField(max_length=255)
		self.field_template = field_template
	
	def formfield(self, **kwargs):
		defaults = {
			'required': False,
			'label': capfirst(self.verbose_name),
			'help_text': self.help_text
		}
		if self.has_default():
			defaults['initial'] = self.default
		defaults.update(kwargs)
		return self.field_template.formfield(**defaults)
	
	def value_from_object(self, obj):
		value = super(JSONAttribute, self).value_from_object(obj)
		if isinstance(self.field_template, (models.DateField, models.DateTimeField)):
			value = self.field_template.to_python(value)
		return value
	
	def get_storage_value(self, value):
		if isinstance(value, datetime.datetime):
			return value.strftime("%Y-%m-%d %H:%M:%S")
		if isinstance(value, datetime.date):
			return value.strftime("%Y-%m-%d")
		return value


class ForeignKeyAttribute(AttributeField):
	value_class = ForeignKeyValue
	
	def __init__(self, model, limit_choices_to=None, **kwargs):
		super(ForeignKeyAttribute, self).__init__(**kwargs)
		self.to = model
		if limit_choices_to is None:
			limit_choices_to = {}
		self.limit_choices_to = limit_choices_to
	
	def validate_value(self, value):
		if value is not None and not isinstance(value, self.to) :
			raise TypeError("The '%s' attribute can only be set to an instance of %s or None." % (self.name, self.to.__name__))
	
	def formfield(self, form_class=forms.ModelChoiceField, **kwargs):
		defaults = {
			'queryset': self.to._default_manager.complex_filter(self.limit_choices_to)
		}
		defaults.update(kwargs)
		return super(ForeignKeyAttribute, self).formfield(form_class=form_class, **defaults)
	
	def value_from_object(self, obj):
		relobj = super(ForeignKeyAttribute, self).value_from_object(obj)
		return getattr(relobj, 'pk', None)
	
	def get_related_field(self):
		"""Spoof being a rel from a ForeignKey."""
		return self.to._meta.pk


class ManyToManyAttribute(ForeignKeyAttribute):
	value_class = ManyToManyValue
	
	def validate_value(self, value):
		if not isinstance(value, models.query.QuerySet) or value.model != self.to:
			raise TypeError("The '%s' attribute can only be set to a %s QuerySet." % (self.name, self.to.__name__))
	
	def formfield(self, form_class=forms.ModelMultipleChoiceField, **kwargs):
		return super(ManyToManyAttribute, self).formfield(form_class=form_class, **kwargs)
	
	def value_from_object(self, obj):
		qs = super(ForeignKeyAttribute, self).value_from_object(obj)
		try:
			return qs.values_list('pk', flat=True)
		except:
			return []