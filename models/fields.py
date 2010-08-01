from django.db import models
from django.db.models import signals
from django.core.exceptions import FieldError
from philo.models.base import Entity


__all__ = ('AttributeField', 'RelationshipField')


class AttributeFieldDescriptor(object):
	def __init__(self, field):
		self.field = field
	
	def __get__(self, instance, owner):
		if instance:
			if self.field.key in instance._added_attribute_registry:
				return instance._added_attribute_registry[self.field.key]
			if self.field.key in instance._removed_attribute_registry:
				return None
			try:
				return instance.attributes[self.field.key]
			except KeyError:
				return None
		else:
			raise AttributeError('The \'%s\' attribute can only be accessed from %s instances.' % (self.field.name, owner.__name__))
	
	def __set__(self, instance, value):
		if self.field.key in instance._removed_attribute_registry:
			instance._removed_attribute_registry.remove(self.field.key)
		instance._added_attribute_registry[self.field.key] = value
	
	def __delete__(self, instance):
		if self.field.key in instance._added_attribute_registry:
			del instance._added_attribute_registry[self.field.key]
		instance._removed_attribute_registry.append(self.field.key)


class AttributeField(object):
	def __init__(self, key):
		self.key = key
	
	def actually_contribute_to_class(self, sender, **kwargs):
		setattr(sender, self.name, AttributeFieldDescriptor(self))
	
	def contribute_to_class(self, cls, name):
		if issubclass(cls, Entity):
			self.name = name
			signals.class_prepared.connect(self.actually_contribute_to_class, sender=cls)
		else:
			raise FieldError('AttributeFields can only be declared on Entity subclasses.')


class RelationshipFieldDescriptor(object):
	def __init__(self, field):
		self.field = field
	
	def __get__(self, instance, owner):
		if instance:
			if self.field.key in instance._added_relationship_registry:
				return instance._added_relationship_registry[self.field.key]
			if self.field.key in instance._removed_relationship_registry:
				return None
			try:
				return instance.relationships[self.field.key]
			except KeyError:
				return None
		else:
			raise AttributeError('The \'%s\' attribute can only be accessed from %s instances.' % (self.field.name, owner.__name__))
	
	def __set__(self, instance, value):
		if isinstance(value, (models.Model, type(None))):
			if self.field.key in instance._removed_relationship_registry:
				instance._removed_relationship_registry.remove(self.field.key)
			instance._added_relationship_registry[self.field.key] = value
		else:
			raise AttributeError('The \'%s\' attribute can only be set using existing Model objects.' % self.field.name)
	
	def __delete__(self, instance):
		if self.field.key in instance._added_relationship_registry:
			del instance._added_relationship_registry[self.field.key]
		instance._removed_relationship_registry.append(self.field.key)


class RelationshipField(object):
	def __init__(self, key):
		self.key = key
	
	def actually_contribute_to_class(self, sender, **kwargs):
		setattr(sender, self.name, RelationshipFieldDescriptor(self))
	
	def contribute_to_class(self, cls, name):
		if issubclass(cls, Entity):
			self.name = name
			signals.class_prepared.connect(self.actually_contribute_to_class, sender=cls)
		else:
			raise FieldError('RelationshipFields can only be declared on Entity subclasses.')