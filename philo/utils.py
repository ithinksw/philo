from UserDict import DictMixin

from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.core.paginator import Paginator, EmptyPage
from django.template import Context
from django.template.loader_tags import ExtendsNode, ConstantIncludeNode


def fattr(*args, **kwargs):
	def wrapper(function):
		for key in kwargs:
			setattr(function, key, kwargs[key])
		return function
	return wrapper


### ContentTypeLimiters


class ContentTypeLimiter(object):
	def q_object(self):
		return models.Q(pk__in=[])
	
	def add_to_query(self, query, *args, **kwargs):
		query.add_q(self.q_object(), *args, **kwargs)


class ContentTypeRegistryLimiter(ContentTypeLimiter):
	def __init__(self):
		self.classes = []
	
	def register_class(self, cls):
		self.classes.append(cls)
	
	def unregister_class(self, cls):
		self.classes.remove(cls)
	
	def q_object(self):
		contenttype_pks = []
		for cls in self.classes:
			try:
				if issubclass(cls, models.Model):
					if not cls._meta.abstract:
						contenttype = ContentType.objects.get_for_model(cls)
						contenttype_pks.append(contenttype.pk)
			except:
				pass
		return models.Q(pk__in=contenttype_pks)


class ContentTypeSubclassLimiter(ContentTypeLimiter):
	def __init__(self, cls, inclusive=False):
		self.cls = cls
		self.inclusive = inclusive
	
	def q_object(self):
		contenttype_pks = []
		def handle_subclasses(cls):
			for subclass in cls.__subclasses__():
				try:
					if issubclass(subclass, models.Model):
						if not subclass._meta.abstract:
							if not self.inclusive and subclass is self.cls:
								continue
							contenttype = ContentType.objects.get_for_model(subclass)
							contenttype_pks.append(contenttype.pk)
					handle_subclasses(subclass)
				except:
					pass
		handle_subclasses(self.cls)
		return models.Q(pk__in=contenttype_pks)


### Pagination


def paginate(objects, per_page=None, page_number=1):
	"""
	Given a list of objects, return a (paginator, page, objects) tuple.
	"""
	try:
		per_page = int(per_page)
	except (TypeError, ValueError):
		# Then either it wasn't set or it was set to an invalid value
		paginator = page = None
	else:
		# There also shouldn't be pagination if the list is too short. Try count()
		# first - good chance it's a queryset, where count is more efficient.
		try:
			if objects.count() <= per_page:
				paginator = page = None
		except AttributeError:
			if len(objects) <= per_page:
				paginator = page = None
	
	try:
		return paginator, page, objects
	except NameError:
		pass
	
	paginator = Paginator(objects, per_page)
	try:
		page_number = int(page_number)
	except:
		page_number = 1
	
	try:
		page = paginator.page(page_number)
	except EmptyPage:
		page = None
	else:
		objects = page.object_list
	
	return paginator, page, objects


### Facilitating template analysis.


LOADED_TEMPLATE_ATTR = '_philo_loaded_template'
BLANK_CONTEXT = Context()


def get_extended(self):
	return self.get_parent(BLANK_CONTEXT)


def get_included(self):
	return self.template


# We ignore the IncludeNode because it will never work in a blank context.
setattr(ExtendsNode, LOADED_TEMPLATE_ATTR, property(get_extended))
setattr(ConstantIncludeNode, LOADED_TEMPLATE_ATTR, property(get_included))


### AttributeMappers


class AttributeMapper(object, DictMixin):
	def __init__(self, entity):
		self.entity = entity
		self.clear_cache()
	
	def __getitem__(self, key):
		if not self._cache_populated:
			self._populate_cache()
		return self._cache[key]
	
	def __setitem__(self, key, value):
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
		return self.entity.attribute_set.all()
	
	def get_attribute(self, key):
		if not self._cache_populated:
			self._populate_cache()
		return self._attributes_cache.get(key, None)
	
	def keys(self):
		if not self._cache_populated:
			self._populate_cache()
		return self._cache.keys()
	
	def items(self):
		if not self._cache_populated:
			self._populate_cache()
		return self._cache.items()
	
	def values(self):
		if not self._cache_populated:
			self._populate_cache()
		return self._cache.values()
	
	def _populate_cache(self):
		if self._cache_populated:
			return
		
		attributes = self.get_attributes()
		value_lookups = {}
		
		for a in attributes:
			value_lookups.setdefault(a.value_content_type, []).append(a.value_object_id)
			self._attributes_cache[a.key] = a
		
		values_bulk = {}
		
		for ct, pks in value_lookups.items():
			values_bulk[ct] = ct.model_class().objects.in_bulk(pks)
		
		self._cache.update(dict([(a.key, getattr(values_bulk[a.value_content_type].get(a.value_object_id), 'value', None)) for a in attributes]))
		self._cache_populated = True
	
	def clear_cache(self):
		self._cache = {}
		self._attributes_cache = {}
		self._cache_populated = False


class LazyAttributeMapperMixin(object):
	def __getitem__(self, key):
		if key not in self._cache and not self._cache_populated:
			self._add_to_cache(key)
		return self._cache[key]
	
	def get_attribute(self, key):
		if key not in self._attributes_cache and not self._cache_populated:
			self._add_to_cache(key)
		return self._attributes_cache[key]
	
	def _add_to_cache(self, key):
		try:
			attr = self.get_attributes().get(key=key)
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
	def get_attributes(self):
		from philo.models import Attribute
		ancestors = dict(self.entity.get_ancestors(include_self=True).values_list('pk', 'level'))
		ct = ContentType.objects.get_for_model(self.entity)
		return sorted(Attribute.objects.filter(entity_content_type=ct, entity_object_id__in=ancestors.keys()), key=lambda x: ancestors[x.entity_object_id])


class LazyTreeAttributeMapper(LazyAttributeMapperMixin, TreeAttributeMapper):
	def get_attributes(self):
		return super(LazyTreeAttributeMapper, self).get_attributes().exclude(key__in=self._cache.keys())


class PassthroughAttributeMapper(AttributeMapper):
	def __init__(self, entities):
		self._attributes = [e.attributes for e in entities]
		super(PassthroughAttributeMapper, self).__init__(self._attributes[0].entity)
	
	def _populate_cache(self):
		if self._cache_populated:
			return
		
		for a in reversed(self._attributes):
			a._populate_cache()
			self._attributes_cache.update(a._attributes_cache)
			self._cache.update(a._cache)
		
		self._cache_populated = True
	
	def get_attributes(self):
		raise NotImplementedError
	
	def clear_cache(self):
		super(PassthroughAttributeMapper, self).clear_cache()
		for a in self._attributes:
			a.clear_cache()


class LazyPassthroughAttributeMapper(LazyAttributeMapperMixin, PassthroughAttributeMapper):
	def _add_to_cache(self, key):
		for a in self._attributes:
			try:
				self._cache[key] = a[key]
				self._attributes_cache[key] = a.get_attribute(key)
			except KeyError:
				pass
			else:
				break
		return self._cache[key]