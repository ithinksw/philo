from functools import partial
from UserDict import DictMixin

from django.db import models
from django.contrib.contenttypes.models import ContentType

from philo.utils.lazycompat import SimpleLazyObject


### AttributeMappers


class AttributeMapper(object, DictMixin):
	"""
	Given an :class:`~philo.models.base.Entity` subclass instance, this class allows dictionary-style access to the :class:`~philo.models.base.Entity`'s :class:`~philo.models.base.Attribute`\ s. In order to prevent unnecessary queries, the :class:`AttributeMapper` will cache all :class:`~philo.models.base.Attribute`\ s and the associated python values when it is first accessed.
	
	:param entity: The :class:`~philo.models.base.Entity` subclass instance whose :class:`~philo.models.base.Attribute`\ s will be made accessible.
	
	"""
	def __init__(self, entity):
		self.entity = entity
		self.clear_cache()
	
	def __getitem__(self, key):
		"""Returns the ultimate python value of the :class:`~philo.models.base.Attribute` with the given ``key`` from the cache, populating the cache if necessary."""
		if not self._cache_filled:
			self._fill_cache()
		return self._cache[key]
	
	def __setitem__(self, key, value):
		"""Given a python value, sets the value of the :class:`~philo.models.base.Attribute` with the given ``key`` to that value."""
		# Prevent circular import.
		from philo.models.base import JSONValue, ForeignKeyValue, ManyToManyValue, Attribute
		old_attr = self.get_attribute(key)
		if old_attr and old_attr.entity_content_type == ContentType.objects.get_for_model(self.entity) and old_attr.entity_object_id == self.entity.pk:
			attribute = old_attr
		else:
			attribute = Attribute(key=key)
			attribute.entity = self.entity
			attribute.full_clean()
		
		if isinstance(value, models.query.QuerySet):
			value_class = ManyToManyValue
		elif isinstance(value, models.Model):
			value_class = ForeignKeyValue
		else:
			value_class = JSONValue
		
		attribute.set_value(value=value, value_class=value_class)
		self._cache[key] = attribute.value.value
		self._attributes_cache[key] = attribute
	
	def get_attributes(self):
		"""Returns an iterable of all of the :class:`~philo.models.base.Entity`'s :class:`~philo.models.base.Attribute`\ s."""
		return self.entity.attribute_set.all()
	
	def get_attribute(self, key, default=None):
		"""Returns the :class:`~philo.models.base.Attribute` instance with the given ``key`` from the cache, populating the cache if necessary, or ``default`` if no such attribute is found."""
		if not self._cache_filled:
			self._fill_cache()
		return self._attributes_cache.get(key, default)
	
	def keys(self):
		"""Returns the keys from the cache, first populating the cache if necessary."""
		if not self._cache_filled:
			self._fill_cache()
		return self._cache.keys()
	
	def items(self):
		"""Returns the items from the cache, first populating the cache if necessary."""
		if not self._cache_filled:
			self._fill_cache()
		return self._cache.items()
	
	def values(self):
		"""Returns the values from the cache, first populating the cache if necessary."""
		if not self._cache_filled:
			self._fill_cache()
		return self._cache.values()
	
	def _fill_cache(self):
		if self._cache_filled:
			return
		
		attributes = self.get_attributes()
		value_lookups = {}
		
		for a in attributes:
			value_lookups.setdefault(a.value_content_type_id, []).append(a.value_object_id)
			self._attributes_cache[a.key] = a
		
		values_bulk = dict(((ct_pk, SimpleLazyObject(partial(ContentType.objects.get_for_id(ct_pk).model_class().objects.in_bulk, pks))) for ct_pk, pks in value_lookups.items()))
		
		cache = {}
		
		for a in attributes:
			cache[a.key] = SimpleLazyObject(partial(self._lazy_value_from_bulk, values_bulk, a))
			a._value_cache = cache[a.key]
		
		self._cache.update(cache)
		self._cache_filled = True
	
	def _lazy_value_from_bulk(self, bulk, attribute):
		v = bulk[attribute.value_content_type_id].get(attribute.value_object_id)
		return getattr(v, 'value', None)
	
	def clear_cache(self):
		"""Clears the cache."""
		self._cache = {}
		self._attributes_cache = {}
		self._cache_filled = False


class LazyAttributeMapperMixin(object):
	"""In some cases, it may be that only one attribute value needs to be fetched. In this case, it is more efficient to avoid populating the cache whenever possible. This mixin overrides the :meth:`__getitem__` and :meth:`get_attribute` methods to prevent their populating the cache. If the cache has been populated (i.e. through :meth:`keys`, :meth:`values`, etc.), then the value or attribute will simply be returned from the cache."""
	def __getitem__(self, key):
		if key not in self._cache and not self._cache_filled:
			self._add_to_cache(key)
		return self._cache[key]
	
	def get_attribute(self, key, default=None):
		if key not in self._attributes_cache and not self._cache_filled:
			self._add_to_cache(key)
		return self._attributes_cache.get(key, default)
	
	def _raw_get_attribute(self, key):
		return self.get_attributes().get(key=key)
	
	def _add_to_cache(self, key):
		from philo.models.base import Attribute
		try:
			attr = self._raw_get_attribute(key)
		except Attribute.DoesNotExist:
			raise KeyError
		else:
			val = getattr(attr.value, 'value', None)
			self._cache[key] = val
			self._attributes_cache[key] = attr


class LazyAttributeMapper(LazyAttributeMapperMixin, AttributeMapper):
	def get_attributes(self):
		return super(LazyAttributeMapper, self).get_attributes().exclude(key__in=self._cache.keys())


class TreeAttributeMapper(AttributeMapper):
	"""The :class:`~philo.models.base.TreeEntity` class allows the inheritance of :class:`~philo.models.base.Attribute`\ s down the tree. This mapper will return the most recently declared :class:`~philo.models.base.Attribute` among the :class:`~philo.models.base.TreeEntity`'s ancestors or set an attribute on the :class:`~philo.models.base.Entity` it is attached to."""
	def get_attributes(self):
		"""Returns a list of :class:`~philo.models.base.Attribute`\ s sorted by increasing parent level. When used to populate the cache, this will cause :class:`~philo.models.base.Attribute`\ s on the root to be overwritten by those on its children, etc."""
		from philo.models import Attribute
		ancestors = dict(self.entity.get_ancestors(include_self=True).values_list('pk', 'level'))
		ct = ContentType.objects.get_for_model(self.entity)
		attrs = Attribute.objects.filter(entity_content_type=ct, entity_object_id__in=ancestors.keys())
		return sorted(attrs, key=lambda x: ancestors[x.entity_object_id])


class LazyTreeAttributeMapper(LazyAttributeMapperMixin, TreeAttributeMapper):
	def get_attributes(self):
		from philo.models import Attribute
		ancestors = dict(self.entity.get_ancestors(include_self=True).values_list('pk', 'level'))
		ct = ContentType.objects.get_for_model(self.entity)
		attrs = Attribute.objects.filter(entity_content_type=ct, entity_object_id__in=ancestors.keys()).exclude(key__in=self._cache.keys())
		return sorted(attrs, key=lambda x: ancestors[x.entity_object_id])
	
	def _raw_get_attribute(self, key):
		from philo.models import Attribute
		ancestors = dict(self.entity.get_ancestors(include_self=True).values_list('pk', 'level'))
		ct = ContentType.objects.get_for_model(self.entity)
		try:
			attrs = Attribute.objects.filter(entity_content_type=ct, entity_object_id__in=ancestors.keys(), key=key)
			sorted_attrs = sorted(attrs, key=lambda x: ancestors[x.entity_object_id], reverse=True)
			return sorted_attrs[0]
		except IndexError:
			raise Attribute.DoesNotExist


class PassthroughAttributeMapper(AttributeMapper):
	"""
	Given an iterable of :class:`Entities <philo.models.base.Entity>`, this mapper will fetch an :class:`AttributeMapper` for each one. Lookups will return the value from the first :class:`AttributeMapper` which has an entry for a given key. Assignments will be made to the first :class:`.Entity` in the iterable.
	
	:param entities: An iterable of :class:`.Entity` subclass instances.
	
	"""
	def __init__(self, entities):
		self._attributes = [e.attributes for e in entities]
		super(PassthroughAttributeMapper, self).__init__(self._attributes[0].entity)
	
	def _fill_cache(self):
		if self._cache_filled:
			return
		
		for a in reversed(self._attributes):
			a._fill_cache()
			self._attributes_cache.update(a._attributes_cache)
			self._cache.update(a._cache)
		
		self._cache_filled = True
	
	def get_attributes(self):
		raise NotImplementedError
	
	def clear_cache(self):
		super(PassthroughAttributeMapper, self).clear_cache()
		for a in self._attributes:
			a.clear_cache()


class LazyPassthroughAttributeMapper(LazyAttributeMapperMixin, PassthroughAttributeMapper):
	"""The :class:`LazyPassthroughAttributeMapper` is lazy in that it tries to avoid accessing the :class:`AttributeMapper`\ s that it uses for lookups. However, those :class:`AttributeMapper`\ s may or may not be lazy themselves."""
	def _raw_get_attribute(self, key):
		from philo.models import Attribute
		for a in self._attributes:
			attr = a.get_attribute(key)
			if attr is not None:
				return attr
		raise Attribute.DoesNotExist