from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic
from django.utils import simplejson as json
from django.core.exceptions import ObjectDoesNotExist
from UserDict import DictMixin


def register_value_model(model):
	pass


def unregister_value_model(model):
	pass


class Attribute(models.Model):
	entity_content_type = models.ForeignKey(ContentType, verbose_name='Entity type')
	entity_object_id = models.PositiveIntegerField(verbose_name='Entity ID')
	entity = generic.GenericForeignKey('entity_content_type', 'entity_object_id')
	key = models.CharField(max_length=255)
	json_value = models.TextField(verbose_name='Value (JSON)', help_text='This value must be valid JSON.')
	
	def get_value(self):
		return json.loads(self.json_value)
	
	def set_value(self, value):
		self.json_value = json.dumps(value)
	
	def delete_value(self):
		self.json_value = json.dumps(None)
	
	value = property(get_value, set_value, delete_value)
	
	def __unicode__(self):
		return u'"%s": %s' % (self.key, self.value)
	
	class Meta:
		app_label = 'philo'


class Relationship(models.Model):
	entity_content_type = models.ForeignKey(ContentType, related_name='relationship_entity_set', verbose_name='Entity type')
	entity_object_id = models.PositiveIntegerField(verbose_name='Entity ID')
	entity = generic.GenericForeignKey('entity_content_type', 'entity_object_id')
	key = models.CharField(max_length=255)
	value_content_type = models.ForeignKey(ContentType, related_name='relationship_value_set', verbose_name='Value type')
	value_object_id = models.PositiveIntegerField(verbose_name='Value ID')
	value = generic.GenericForeignKey('value_content_type', 'value_object_id')
	
	def __unicode__(self):
		return u'"%s": %s' % (self.key, self.value)
	
	class Meta:
		app_label = 'philo'


class QuerySetMapper(object, DictMixin):
	def __init__(self, queryset, passthrough=None):
		self.queryset = queryset
		self.passthrough = passthrough
	def __getitem__(self, key):
		try:
			return self.queryset.get(key__exact=key).value
		except ObjectDoesNotExist:
			if self.passthrough:
				return self.passthrough.__getitem__(key)
			raise KeyError
	def keys(self):
		keys = set(self.queryset.values_list('key', flat=True).distinct())
		if self.passthrough:
			keys += set(self.passthrough.keys())
		return list(keys)


class Entity(models.Model):
	attribute_set = generic.GenericRelation(Attribute, content_type_field='entity_content_type', object_id_field='entity_object_id')
	relationship_set = generic.GenericRelation(Relationship, content_type_field='entity_content_type', object_id_field='entity_object_id')
	
	@property
	def attributes(self):
		return QuerySetMapper(self.attribute_set)
	
	@property
	def relationships(self):
		return QuerySetMapper(self.relationship_set)
	
	class Meta:
		abstract = True
		app_label = 'philo'


class TreeManager(models.Manager):
	use_for_related_fields = True
	
	def roots(self):
		return self.filter(parent__isnull=True)
	
	def get_with_path(self, path, root=None, absolute_result=True, pathsep='/'):
		"""
		Returns the object with the path, or None if there is no object with that path,
		unless absolute_result is set to False, in which case it returns a tuple containing
		the deepest object found along the path, and the remainder of the path after that
		object as a string (or None in the case that there is no remaining path).
		"""
		slugs = path.split(pathsep)
		obj = root
		remaining_slugs = list(slugs)
		remainder = None
		for slug in slugs:
			remaining_slugs.remove(slug)
			if slug: # ignore blank slugs, handles for multiple consecutive pathseps
				try:
					obj = self.get(slug__exact=slug, parent__exact=obj)
				except self.model.DoesNotExist:
					if absolute_result:
						obj = None
					remaining_slugs.insert(0, slug)
					remainder = pathsep.join(remaining_slugs)
					break
		if obj:
			if absolute_result:
				return obj
			else:
				return (obj, remainder)
		raise self.model.DoesNotExist('%s matching query does not exist.' % self.model._meta.object_name)


class TreeModel(models.Model):
	objects = TreeManager()
	parent = models.ForeignKey('self', related_name='children', null=True, blank=True)
	slug = models.SlugField()
	
	def get_path(self, pathsep='/', field='slug'):
		path = getattr(self, field, '?')
		parent = self.parent
		while parent:
			path = getattr(parent, field, '?') + pathsep + path
			parent = parent.parent
		return path
	path = property(get_path)
	
	def __unicode__(self):
		return self.path
	
	class Meta:
		abstract = True
		app_label = 'philo'


class TreeEntity(TreeModel, Entity):
	@property
	def attributes(self):
		if self.parent:
			return QuerySetMapper(self.attribute_set, passthrough=self.parent.attributes)
		return super(TreeEntity, self).attributes
	
	@property
	def relationships(self):
		if self.parent:
			return QuerySetMapper(self.relationship_set, passthrough=self.parent.relationships)
		return super(TreeEntity, self).relationships
	
	class Meta:
		abstract = True
		app_label = 'philo'


class InheritableTreeEntity(TreeEntity):
	instance_type = models.ForeignKey(ContentType, editable=False)
	
	def save(self, force_insert=False, force_update=False):
		if not hasattr(self, 'instance_type_ptr'):
			self.instance_type = ContentType.objects.get_for_model(self.__class__)
		super(InheritableTreeEntity, self).save(force_insert, force_update)
	
	@property
	def instance(self):
		try:
			return self.instance_type.get_object_for_this_type(id=self.id)
		except:
			return None
	
	def get_path(self, pathsep='/', field='slug'):
		path = getattr(self.instance, field, getattr(self.instance, 'slug', '?'))
		parent = self.parent
		while parent:
			path = getattr(parent.instance, field, getattr(parent.instance, 'slug', '?')) + pathsep + path
			parent = parent.parent
		return path
	path = property(get_path)
	
	@property
	def attributes(self):
		if self.parent:
			return QuerySetMapper(self.instance.attribute_set, passthrough=self.parent.instance.attributes)
		return QuerySetMapper(self.instance.attribute_set)

	@property
	def relationships(self):
		if self.parent:
			return QuerySetMapper(self.instance.relationship_set, passthrough=self.parent.instance.relationships)
		return QuerySetMapper(self.instance.relationship_set)
	
	class Meta:
		abstract = True
		app_label = 'philo'