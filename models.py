# encoding: utf-8
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.models import User, Group
from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.contrib.sites.models import Site
from utils import fattr
from django.template import add_to_builtins as register_templatetags
from django.template import Template as DjangoTemplate
from django.template import TemplateDoesNotExist
from django.template import Context, RequestContext
from django.core.exceptions import ObjectDoesNotExist
try:
	import json
except ImportError:
	import simplejson as json
from UserDict import DictMixin
from templatetags.containers import ContainerNode
from django.template.loader_tags import ExtendsNode, ConstantIncludeNode, IncludeNode
from django.template.loader import get_template
from django.http import Http404, HttpResponse, HttpResponseServerError, HttpResponseRedirect
from django.core.servers.basehttp import FileWrapper


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


class Collection(models.Model):
	name = models.CharField(max_length=255)
	description = models.TextField(blank=True, null=True)


class CollectionMemberManager(models.Manager):
	use_for_related_fields = True

	def with_model(self, model):
		return model._default_manager.filter(pk__in=self.filter(member_content_type=ContentType.objects.get_for_model(model)).values_list('member_object_id', flat=True))


class CollectionMember(models.Model):
	objects = CollectionMemberManager()
	collection = models.ForeignKey(Collection, related_name='members')
	index = models.PositiveIntegerField(verbose_name='Index', help_text='This will determine the ordering of the item within the collection. (Optional)', null=True, blank=True)
	member_content_type = models.ForeignKey(ContentType, verbose_name='Member type')
	member_object_id = models.PositiveIntegerField(verbose_name='Member ID')
	member = generic.GenericForeignKey('member_content_type', 'member_object_id')


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


class Node(TreeEntity):
	instance_type = models.ForeignKey(ContentType, editable=False)
	
	def get_path(self, pathsep='/', field='slug'):
		path = getattr(self.instance, field, '?')
		parent = self.parent
		while parent:
			path = getattr(parent.instance, field, '?') + pathsep + path
			parent = parent.parent
		return path
	path = property(get_path)
	
	def save(self, force_insert=False, force_update=False):
		if not hasattr(self, 'instance_type_ptr'):
			self.instance_type = ContentType.objects.get_for_model(self.__class__)
		super(Node, self).save(force_insert, force_update)
	
	@property
	def instance(self):
		return self.instance_type.get_object_for_this_type(id=self.id)
	
	accepts_subpath = False
	
	def render_to_response(self, request, path=None, subpath=None):
		return HttpResponseServerError()


class MultiNode(Node):
	accepts_subpath = True
	
	urlpatterns = []
	
	def render_to_response(self, request, path=None, subpath=None):
		if not subpath:
			subpath = ""
		subpath = "/" + subpath
		from django.core.urlresolvers import resolve
		view, args, kwargs = resolve(subpath, urlconf=self)
		return view(request, *args, **kwargs)
	
	class Meta:
		abstract = True


class Redirect(Node):
	STATUS_CODES = (
		(302, 'Temporary'),
		(301, 'Permanent'),
	)
	target = models.URLField()
	status_code = models.IntegerField(choices=STATUS_CODES, default=302, verbose_name='redirect type')
	
	def render_to_response(self, request, path=None, subpath=None):
		response = HttpResponseRedirect(self.target)
		response.status_code = self.status_code
		return response


class File(Node):
	""" For storing arbitrary files """
	mimetype = models.CharField(max_length=255)
	file = models.FileField(upload_to='philo/files/%Y/%m/%d')
	
	def render_to_response(self, request, path=None, subpath=None):
		wrapper = FileWrapper(self.file)
		response = HttpResponse(wrapper, content_type=self.mimetype)
		response['Content-Length'] = self.file.size
		return response


class Template(TreeModel):
	name = models.CharField(max_length=255)
	documentation = models.TextField(null=True, blank=True)
	mimetype = models.CharField(max_length=255, null=True, blank=True)
	code = models.TextField()
	
	@property
	def origin(self):
		return 'philo.models.Template: ' + self.path
	
	@property
	def django_template(self):
		return DjangoTemplate(self.code)
	
	@property
	def containers(self):
		"""
		Returns a list of names of contentlets referenced by containers. 
		This will break if there is a recursive extends or includes in the template code.
		Due to the use of an empty Context, any extends or include tags with dynamic arguments probably won't work.
		"""
		def container_node_names(template):
			def nodelist_container_node_names(nodelist):
				names = []
				for node in nodelist:
					try:
						for nodelist_name in ('nodelist', 'nodelist_loop', 'nodelist_empty', 'nodelist_true', 'nodelist_false'):
							if hasattr(node, nodelist_name):
								names.extend(nodelist_container_node_names(getattr(node, nodelist_name)))
						if isinstance(node, ContainerNode):
							names.append(node.name)
						elif isinstance(node, ExtendsNode):
							extended_template = node.get_parent(Context())
							if extended_template:
								names.extend(container_node_names(extended_template))
						elif isinstance(node, ConstantIncludeNode):
							included_template = node.template
							if included_template:
								names.extend(container_node_names(included_template))
						elif isinstance(node, IncludeNode):
							included_template = get_template(node.template_name.resolve(Context()))
							if included_template:
								names.extend(container_node_names(included_template))
					except:
						pass # fail for this node
				return names
			return nodelist_container_node_names(template.nodelist)
		return set(container_node_names(self.django_template))
	
	def __unicode__(self):
		return self.get_path(u' › ', 'name')
	
	@staticmethod
	@fattr(is_usable=True)
	def loader(template_name, template_dirs=None): # load_template_source
		try:
			template = Template.objects.get_with_path(template_name)
		except Template.DoesNotExist:
			raise TemplateDoesNotExist(template_name)
		return (template.code, template.origin)


class Page(Node):
	template = models.ForeignKey(Template, related_name='pages')
	title = models.CharField(max_length=255)
	
	def render_to_response(self, request, path=None, subpath=None):
		return HttpResponse(self.template.django_template.render(RequestContext(request, {'page': self})), mimetype=self.template.mimetype)
	
	def __unicode__(self):
		return self.get_path(u' › ', 'title')


# the following line enables the selection of a node as the root for a given django.contrib.sites Site object
models.ForeignKey(Node, related_name='sites', null=True, blank=True).contribute_to_class(Site, 'root_node')


class Contentlet(models.Model):
	page = models.ForeignKey(Page, related_name='contentlets')
	name = models.CharField(max_length=255)
	content = models.TextField()
	dynamic = models.BooleanField(default=False)


register_templatetags('philo.templatetags.containers')


register_value_model(User)
register_value_model(Group)
register_value_model(Site)
register_value_model(Collection)
register_value_model(Template)
register_value_model(Page)
