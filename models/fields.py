from django.db import models
from django.db.models import signals
from django.core.exceptions import ObjectDoesNotExist, FieldError
from django.contrib.contenttypes.models import ContentType
from functools import partial
from philo.models.base import Attribute, Relationship, Entity


__all__ = ('AttributeField', 'RelationshipField')


class AttributeFieldDescriptor(object):
	def __init__(self, field):
		self.field = field
	
	def __get__(self, instance, owner):
		if instance:
			try:
				return instance.attribute_set.get(key__exact=self.field.key).value
			except ObjectDoesNotExist:
				return None
		else:
			raise AttributeError('The \'%s\' attribute can only be accessed from %s instances.' % (self.field.name, owner.__name__))
	
	def __set__(self, instance, value):
		try:
			attribute = instance.attribute_set.get(key__exact=self.field.key)
		except ObjectDoesNotExist:
			attribute = Attribute()
			attribute.entity = instance
			attribute.key = self.field.key
		attribute.value = value
		attribute.save()
	
	def __delete__(self, instance):
		instance.attribute_set.filter(key__exact=self.field.key).delete()


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
			try:
				return instance.relationship_set.get(key__exact=self.field.key).value
			except ObjectDoesNotExist:
				return None
		else:
			raise AttributeError('The \'%s\' attribute can only be accessed from %s instances.' % (self.field.name, owner.__name__))
	
	def __set__(self, instance, value):
		if isinstance(value, (models.Model, type(None))):
			try:
				relationship = instance.relationship_set.get(key__exact=self.field.key)
			except ObjectDoesNotExist:
				relationship = Relationship()
				relationship.entity = instance
				relationship.key = self.field.key
			relationship.value = value
			relationship.save()
		else:
			raise AttributeError('The \'%\' attribute can only be set using existing Model objects.' % self.field.name)
	
	def __delete__(self, instance):
		instance.relationship_set.filter(key__exact=self.field.key).delete()


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