from django import forms
from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic
from django.utils import simplejson as json
from django.core.exceptions import ObjectDoesNotExist
from philo.exceptions import AncestorDoesNotExist
from philo.models.fields import JSONField
from philo.utils import ContentTypeRegistryLimiter, ContentTypeSubclassLimiter
from philo.signals import entity_class_prepared
from philo.validators import json_validator
from UserDict import DictMixin
from mptt.models import MPTTModel, MPTTModelBase, MPTTOptions


class Tag(models.Model):
	name = models.CharField(max_length=255)
	slug = models.SlugField(max_length=255, unique=True)
	
	def __unicode__(self):
		return self.name
	
	class Meta:
		app_label = 'philo'


class Titled(models.Model):
	title = models.CharField(max_length=255)
	slug = models.SlugField(max_length=255)
	
	def __unicode__(self):
		return self.title
	
	class Meta:
		abstract = True


value_content_type_limiter = ContentTypeRegistryLimiter()


def register_value_model(model):
	value_content_type_limiter.register_class(model)


def unregister_value_model(model):
	value_content_type_limiter.unregister_class(model)


class AttributeValue(models.Model):
	attribute_set = generic.GenericRelation('Attribute', content_type_field='value_content_type', object_id_field='value_object_id')
	
	@property
	def attribute(self):
		return self.attribute_set.all()[0]
	
	def apply_data(self, data):
		raise NotImplementedError
	
	def value_formfield(self, **kwargs):
		raise NotImplementedError
	
	def __unicode__(self):
		return unicode(self.value)
	
	class Meta:
		abstract = True


attribute_value_limiter = ContentTypeSubclassLimiter(AttributeValue)


class JSONValue(AttributeValue):
	value = JSONField() #verbose_name='Value (JSON)', help_text='This value must be valid JSON.')
	
	def __unicode__(self):
		return self.value_json
	
	def value_formfield(self, **kwargs):
		kwargs['initial'] = self.value_json
		return self._meta.get_field('value').formfield(**kwargs)
	
	def apply_data(self, cleaned_data):
		self.value = cleaned_data.get('value', None)
	
	class Meta:
		app_label = 'philo'


class ForeignKeyValue(AttributeValue):
	content_type = models.ForeignKey(ContentType, limit_choices_to=value_content_type_limiter, verbose_name='Value type', null=True, blank=True)
	object_id = models.PositiveIntegerField(verbose_name='Value ID', null=True, blank=True)
	value = generic.GenericForeignKey()
	
	def value_formfield(self, form_class=forms.ModelChoiceField, **kwargs):
		if self.content_type is None:
			return None
		kwargs.update({'initial': self.object_id, 'required': False})
		return form_class(self.content_type.model_class()._default_manager.all(), **kwargs)
	
	def apply_data(self, cleaned_data):
		if 'value' in cleaned_data and cleaned_data['value'] is not None:
			self.value = cleaned_data['value']
		else:
			self.content_type = cleaned_data.get('content_type', None)
			# If there is no value set in the cleaned data, clear the stored value.
			self.object_id = None
	
	class Meta:
		app_label = 'philo'


class ManyToManyValue(AttributeValue):
	content_type = models.ForeignKey(ContentType, limit_choices_to=value_content_type_limiter, verbose_name='Value type', null=True, blank=True)
	values = models.ManyToManyField(ForeignKeyValue, blank=True, null=True)
	
	def get_object_id_list(self):
		if not self.values.count():
			return []
		else:
			return self.values.values_list('object_id', flat=True)
	
	def get_value(self):
		if self.content_type is None:
			return None
		
		return self.content_type.model_class()._default_manager.filter(id__in=self.get_object_id_list())
	
	def set_value(self, value):
		# Value is probably a queryset - but allow any iterable.
		
		# These lines shouldn't be necessary; however, if value is an EmptyQuerySet,
		# the code (specifically the object_id__in query) won't work without them. Unclear why...
		if not value:
			value = []
		
		# Before we can fiddle with the many-to-many to foreignkeyvalues, we need
		# a pk.
		if self.pk is None:
			self.save()
		
		if isinstance(value, models.query.QuerySet):
			value = value.values_list('id', flat=True)
		
		self.values.filter(~models.Q(object_id__in=value)).delete()
		current = self.get_object_id_list()
		
		for v in value:
			if v in current:
				continue
			self.values.create(content_type=self.content_type, object_id=v)
	
	value = property(get_value, set_value)
	
	def value_formfield(self, form_class=forms.ModelMultipleChoiceField, **kwargs):
		if self.content_type is None:
			return None
		kwargs.update({'initial': self.get_object_id_list(), 'required': False})
		return form_class(self.content_type.model_class()._default_manager.all(), **kwargs)
	
	def apply_data(self, cleaned_data):
		if 'value' in cleaned_data and cleaned_data['value'] is not None:
			self.value = cleaned_data['value']
		else:
			self.content_type = cleaned_data.get('content_type', None)
			# If there is no value set in the cleaned data, clear the stored value.
			self.value = []
	
	class Meta:
		app_label = 'philo'


class Attribute(models.Model):
	entity_content_type = models.ForeignKey(ContentType, related_name='attribute_entity_set', verbose_name='Entity type')
	entity_object_id = models.PositiveIntegerField(verbose_name='Entity ID')
	entity = generic.GenericForeignKey('entity_content_type', 'entity_object_id')
	
	value_content_type = models.ForeignKey(ContentType, related_name='attribute_value_set', limit_choices_to=attribute_value_limiter, verbose_name='Value type', null=True, blank=True)
	value_object_id = models.PositiveIntegerField(verbose_name='Value ID', null=True, blank=True)
	value = generic.GenericForeignKey('value_content_type', 'value_object_id')
	
	key = models.CharField(max_length=255)
	
	def __unicode__(self):
		return u'"%s": %s' % (self.key, self.value)
	
	class Meta:
		app_label = 'philo'
		unique_together = (('key', 'entity_content_type', 'entity_object_id'), ('value_content_type', 'value_object_id'))


class QuerySetMapper(object, DictMixin):
	def __init__(self, queryset, passthrough=None):
		self.queryset = queryset
		self.passthrough = passthrough
	
	def __getitem__(self, key):
		try:
			value = self.queryset.get(key__exact=key).value
		except ObjectDoesNotExist:
			if self.passthrough is not None:
				return self.passthrough.__getitem__(key)
			raise KeyError
		else:
			if value is not None:
				return value.value
			return value
	
	def keys(self):
		keys = set(self.queryset.values_list('key', flat=True).distinct())
		if self.passthrough is not None:
			keys |= set(self.passthrough.keys())
		return list(keys)


class EntityOptions(object):
	def __init__(self, options):
		if options is not None:
			for key, value in options.__dict__.items():
				setattr(self, key, value)
		if not hasattr(self, 'proxy_fields'):
			self.proxy_fields = []
	
	def add_proxy_field(self, proxy_field):
		self.proxy_fields.append(proxy_field)


class EntityBase(models.base.ModelBase):
	def __new__(cls, name, bases, attrs):
		new = super(EntityBase, cls).__new__(cls, name, bases, attrs)
		entity_options = attrs.pop('EntityMeta', None)
		setattr(new, '_entity_meta', EntityOptions(entity_options))
		entity_class_prepared.send(sender=new)
		return new


class Entity(models.Model):
	__metaclass__ = EntityBase
	
	attribute_set = generic.GenericRelation(Attribute, content_type_field='entity_content_type', object_id_field='entity_object_id')
	
	@property
	def attributes(self):
		return QuerySetMapper(self.attribute_set.all())
	
	@property
	def _added_attribute_registry(self):
		if not hasattr(self, '_real_added_attribute_registry'):
			self._real_added_attribute_registry = {}
		return self._real_added_attribute_registry
	
	@property
	def _removed_attribute_registry(self):
		if not hasattr(self, '_real_removed_attribute_registry'):
			self._real_removed_attribute_registry = []
		return self._real_removed_attribute_registry
	
	def save(self, *args, **kwargs):
		super(Entity, self).save(*args, **kwargs)
		
		for key in self._removed_attribute_registry:
			self.attribute_set.filter(key__exact=key).delete()
		del self._removed_attribute_registry[:]
		
		for field, value in self._added_attribute_registry.items():
			try:
				attribute = self.attribute_set.get(key__exact=field.key)
			except Attribute.DoesNotExist:
				attribute = Attribute()
				attribute.entity = self
				attribute.key = field.key
			
			field.set_attribute_value(attribute, value)
			attribute.save()
		self._added_attribute_registry.clear()
	
	class Meta:
		abstract = True


class TreeManager(models.Manager):
	use_for_related_fields = True
	
	def get_with_path(self, path, root=None, absolute_result=True, pathsep='/', field='slug'):
		"""
		Returns the object with the path, unless absolute_result is set to False, in which
		case it returns a tuple containing the deepest object found along the path, and the
		remainder of the path after that object as a string (or None if there is no remaining
		path). Raises a DoesNotExist exception if no object is found with the given path.
		
		If the path you're searching for is known to exist, it is always faster to use
		absolute_result=True - unless the path depth is over ~40, in which case the high cost
		of the absolute query makes a binary search (i.e. non-absolute) faster.
		"""
		# Note: SQLite allows max of 64 tables in one join. That means the binary search will
		# only work on paths with a max depth of 127 and the absolute fetch will only work
		# to a max depth of (surprise!) 63. Although this could be handled, chances are your
		# tree structure won't be that deep.
		segments = path.split(pathsep)
		
		# Check for a trailing pathsep so we can restore it later.
		trailing_pathsep = False
		if segments[-1] == '':
			trailing_pathsep = True
		
		# Clean out blank segments. Handles multiple consecutive pathseps.
		while True:
			try:
				segments.remove('')
			except ValueError:
				break
		
		# Special-case a lack of segments. No queries necessary.
		if not segments:
			if root is not None:
				if absolute_result:
					return root
				return root, None
			else:
				raise self.model.DoesNotExist('%s matching query does not exist.' % self.model._meta.object_name)
		
		def make_query_kwargs(segments, root):
			kwargs = {}
			prefix = ""
			revsegs = list(segments)
			revsegs.reverse()
			
			for segment in revsegs:
				kwargs["%s%s__exact" % (prefix, field)] = segment
				prefix += "parent__"
			
			if prefix:
				kwargs[prefix[:-2]] = root
			
			return kwargs
		
		def build_path(segments):
			path = pathsep.join(segments)
			if trailing_pathsep and segments and segments[-1] != '':
				path += pathsep
			return path
		
		def find_obj(segments, depth, deepest_found=None):
			if deepest_found is None:
				deepest_level = 0
			elif root is None:
				deepest_level = deepest_found.get_level() + 1
			else:
				deepest_level = deepest_found.get_level() - root.get_level()
			try:
				obj = self.get(**make_query_kwargs(segments[deepest_level:depth], deepest_found or root))
			except self.model.DoesNotExist:
				if not deepest_level and depth > 1:
					# make sure there's a root node...
					depth = 1
				else:
					# Try finding one with half the path since the deepest find.
					depth = (deepest_level + depth)/2
				
				if deepest_level == depth:
					# This should happen if nothing is found with any part of the given path.
					if root is not None and deepest_found is None:
						return root, build_path(segments)
					raise
				
				return find_obj(segments, depth, deepest_found)
			else:
				# Yay! Found one!
				if root is None:
					deepest_level = obj.get_level() + 1
				else:
					deepest_level = obj.get_level() - root.get_level()
				
				# Could there be a deeper one?
				if obj.is_leaf_node():
					return obj, build_path(segments[deepest_level:]) or None
				
				depth += (len(segments) - depth)/2 or len(segments) - depth
				
				if depth > deepest_level + obj.get_descendant_count():
					depth = deepest_level + obj.get_descendant_count()
				
				if deepest_level == depth:
					return obj, build_path(segments[deepest_level:]) or None
				
				try:
					return find_obj(segments, depth, obj)
				except self.model.DoesNotExist:
					# Then this was the deepest.
					return obj, build_path(segments[deepest_level:])
		
		if absolute_result:
			return self.get(**make_query_kwargs(segments, root))
		
		# Try a modified binary search algorithm. Feed the root in so that query complexity
		# can be reduced. It might be possible to weight the search towards the beginning
		# of the path, since short paths are more likely, but how far forward? It would
		# need to shift depending on len(segments) - perhaps logarithmically?
		return find_obj(segments, len(segments)/2 or len(segments))


class TreeModel(MPTTModel):
	objects = TreeManager()
	parent = models.ForeignKey('self', related_name='children', null=True, blank=True)
	slug = models.SlugField(max_length=255)
	
	def get_path(self, root=None, pathsep='/', field='slug'):
		if root == self:
			return ''
		
		if root is not None and not self.is_descendant_of(root):
			raise AncestorDoesNotExist(root)
		
		qs = self.get_ancestors()
		
		if root is not None:
			qs = qs.filter(**{'%s__gt' % self._mptt_meta.level_attr: root.get_level()})
		
		return pathsep.join([getattr(parent, field, '?') for parent in list(qs) + [self]])
	path = property(get_path)
	
	def __unicode__(self):
		return self.path
	
	class Meta:
		unique_together = (('parent', 'slug'),)
		abstract = True


class TreeEntityBase(MPTTModelBase, EntityBase):
	def __new__(meta, name, bases, attrs):
		attrs['_mptt_meta'] = MPTTOptions(attrs.pop('MPTTMeta', None))
		cls = EntityBase.__new__(meta, name, bases, attrs)
		
		return meta.register(cls)


class TreeEntity(Entity, TreeModel):
	__metaclass__ = TreeEntityBase
	
	@property
	def attributes(self):
		if self.parent:
			return QuerySetMapper(self.attribute_set.all(), passthrough=self.parent.attributes)
		return super(TreeEntity, self).attributes
	
	class Meta:
		abstract = True