from django import forms
from django.core.exceptions import FieldError, ValidationError
from django.db import models
from django.db.models.fields import NOT_PROVIDED
from django.utils import simplejson as json
from django.utils.text import capfirst
from philo.signals import entity_class_prepared
from philo.validators import TemplateValidator, json_validator


__all__ = ('JSONAttribute', 'ForeignKeyAttribute', 'ManyToManyAttribute')


class EntityProxyField(object):
	descriptor_class = None
	
	def __init__(self, verbose_name=None, help_text=None, default=NOT_PROVIDED, editable=True, *args, **kwargs):
		if self.descriptor_class is None:
			raise NotImplementedError('EntityProxyField subclasses must specify a descriptor_class.')
		self.verbose_name = verbose_name
		self.help_text = help_text
		self.default = default
		self.editable = editable
	
	def actually_contribute_to_class(self, sender, **kwargs):
		sender._entity_meta.add_proxy_field(self)
		setattr(sender, self.attname, self.descriptor_class(self))
	
	def contribute_to_class(self, cls, name):
		from philo.models.base import Entity
		if issubclass(cls, Entity):
			self.name = name
			self.attname = name
			if self.verbose_name is None and name:
				self.verbose_name = name.replace('_', ' ')
			entity_class_prepared.connect(self.actually_contribute_to_class, sender=cls)
		else:
			raise FieldError('%s instances can only be declared on Entity subclasses.' % self.__class__.__name__)
	
	def formfield(self, *args, **kwargs):
		raise NotImplementedError('EntityProxyField subclasses must implement a formfield method.')
	
	def value_from_object(self, obj):
		return getattr(obj, self.attname)
	
	def has_default(self):
		return self.default is not NOT_PROVIDED


class AttributeFieldDescriptor(object):
	def __init__(self, field):
		self.field = field
	
	def __get__(self, instance, owner):
		if instance:
			if self.field in instance._added_attribute_registry:
				return instance._added_attribute_registry[self.field]
			if self.field in instance._removed_attribute_registry:
				return None
			try:
				return instance.attributes[self.field.key]
			except KeyError:
				return None
		else:
			return None
	
	def __set__(self, instance, value):
		raise NotImplementedError('AttributeFieldDescriptor subclasses must implement a __set__ method.')
	
	def __delete__(self, instance):
		if self.field in instance._added_attribute_registry:
			del instance._added_attribute_registry[self.field]
		instance._removed_attribute_registry.append(self.field)


class JSONAttributeDescriptor(AttributeFieldDescriptor):
	def __set__(self, instance, value):
		if self.field in instance._removed_attribute_registry:
			instance._removed_attribute_registry.remove(self.field)
		instance._added_attribute_registry[self.field] = value


class ForeignKeyAttributeDescriptor(AttributeFieldDescriptor):
	def __set__(self, instance, value):
		if isinstance(value, (models.Model, type(None))):
			if self.field in instance._removed_attribute_registry:
				instance._removed_attribute_registry.remove(self.field)
			instance._added_attribute_registry[self.field] = value
		else:
			raise AttributeError('The \'%s\' attribute can only be set using existing Model objects.' % self.field.name)


class ManyToManyAttributeDescriptor(AttributeFieldDescriptor):
	def __set__(self, instance, value):
		if isinstance(value, models.QuerySet):
			if self.field in instance._removed_attribute_registry:
				instance._removed_attribute_registry.remove(self.field)
			instance._added_attribute_registry[self.field] = value
		else:
			raise AttributeError('The \'%s\' attribute can only be set to a QuerySet.' % self.field.name)


class AttributeField(EntityProxyField):
	def contribute_to_class(self, cls, name):
		super(AttributeField, self).contribute_to_class(cls, name)
		if self.key is None:
			self.key = name
	
	def set_attribute_value(self, attribute, value, value_class):
		if not isinstance(attribute.value, value_class):
			if isinstance(attribute.value, models.Model):
				attribute.value.delete()
			new_value = value_class()
		else:
			new_value = attribute.value
		new_value.value = value
		new_value.save()
		attribute.value = new_value


class JSONAttribute(AttributeField):
	descriptor_class = JSONAttributeDescriptor
	
	def __init__(self, field_template=None, key=None, **kwargs):
		super(AttributeField, self).__init__(**kwargs)
		self.key = key
		if field_template is None:
			field_template = models.CharField(max_length=255)
		self.field_template = field_template
	
	def formfield(self, **kwargs):
		defaults = {'required': False, 'label': capfirst(self.verbose_name), 'help_text': self.help_text}
		if self.has_default():
			defaults['initial'] = self.default
		defaults.update(kwargs)
		return self.field_template.formfield(**defaults)
	
	def value_from_object(self, obj):
		try:
			return getattr(obj, self.attname)
		except AttributeError:
			return None
	
	def set_attribute_value(self, attribute, value, value_class=None):
		if value_class is None:
			from philo.models.base import JSONValue
			value_class = JSONValue
		super(JSONAttribute, self).set_attribute_value(attribute, value, value_class)


class ForeignKeyAttribute(AttributeField):
	descriptor_class = ForeignKeyAttributeDescriptor
	
	def __init__(self, model, limit_choices_to=None, key=None, **kwargs):
		super(ForeignKeyAttribute, self).__init__(**kwargs)
		self.key = key
		self.model = model
		if limit_choices_to is None:
			limit_choices_to = {}
		self.limit_choices_to = limit_choices_to
	
	def formfield(self, form_class=forms.ModelChoiceField, **kwargs):
		defaults = {'required': False, 'label': capfirst(self.verbose_name), 'help_text': self.help_text}
		if self.has_default():
			defaults['initial'] = self.default
		defaults.update(kwargs)
		return form_class(self.model._default_manager.complex_filter(self.limit_choices_to), **defaults)
	
	def value_from_object(self, obj):
		try:
			relobj = super(ForeignKeyAttribute, self).value_from_object(obj)
		except AttributeError:
			return None
		return getattr(relobj, 'pk', None)
	
	def set_attribute_value(self, attribute, value, value_class=None):
		if value_class is None:
			from philo.models.base import ForeignKeyValue
			value_class = ForeignKeyValue
		super(ForeignKeyAttribute, self).set_attribute_value(attribute, value, value_class)


class ManyToManyAttribute(ForeignKeyAttribute):
	descriptor_class = ManyToManyAttributeDescriptor
	
	def formfield(self, form_class=forms.ModelMultipleChoiceField, **kwargs):
		return super(ManyToManyAttribute, self).formfield(form_class, **kwargs)
	
	def set_attribute_value(self, attribute, value, value_class=None):
		if value_class is None:
			from philo.models.base import ManyToManyValue
			value_class = ManyToManyValue
		super(ManyToManyAttribute, self).set_attribute_value(attribute, value, value_class)


class TemplateField(models.TextField):
	def __init__(self, allow=None, disallow=None, secure=True, *args, **kwargs):
		super(TemplateField, self).__init__(*args, **kwargs)
		self.validators.append(TemplateValidator(allow, disallow, secure))


class JSONFormField(forms.Field):
	def clean(self, value):
		try:
			return json.loads(value)
		except Exception, e:
			raise ValidationError(u'JSON decode error: %s' % e)


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
	def __init__(self, *args, **kwargs):
		super(JSONField, self).__init__(*args, **kwargs)
		self.validators.append(json_validator)
	
	def get_attname(self):
		return "%s_json" % self.name
	
	def contribute_to_class(self, cls, name):
		super(JSONField, self).contribute_to_class(cls, name)
		setattr(cls, name, JSONDescriptor(self))
	
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