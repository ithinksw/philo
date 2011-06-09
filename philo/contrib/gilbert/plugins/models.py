from django.conf import settings
from django.contrib.admin.util import lookup_field, label_for_field, display_for_field, NestedObjects
from django.core.exceptions import PermissionDenied
from django.db import router
from django.db.models import Q
from django.db.models.fields.related import ManyToOneRel
from django.db.models.fields.files import FieldFile, ImageFieldFile, FileField
from django.forms.models import ModelForm, modelform_factory
from django.template.defaultfilters import capfirst
from django.utils import simplejson as json
from django.utils.encoding import smart_unicode
from .base import Plugin
from ..extdirect import ext_action, ext_method
import operator


@ext_action(name='models')
class Models(Plugin):
	"""
	Plugin providing model-related UI and functionality on the client
	side.
	
	"""
	
	@property
	def index_js_urls(self):
		return super(Models, self).index_js_urls + [
			settings.STATIC_URL + 'gilbert/extjs/examples/ux/SearchField.js',
			settings.STATIC_URL + 'gilbert/plugins/models.js',
		]
	
	@property
	def icon_names(self):
		return super(Models, self).icon_names + [
			'databases',
			'database',
			'plus',
			'minus',
			'gear',
			'pencil',
			'database-import',
			'block',
		]


@ext_action
class ModelAdmin(Plugin):
	"""
	Default ModelAdmin class used by Sites to expose a model-centric API
	on the client side.
	
	"""
	
	form = ModelForm
	icon_name = 'block'
	search_fields = ()
	data_columns = ('__unicode__',)
	data_editable_columns = ()
	
	def __init__(self, site, model):
		super(ModelAdmin, self).__init__(site)
		self.model = model
		self.model_meta = model._meta
	
	@classmethod
	def data_serialize_model_instance(cls, obj):
		return {
			'app_label': obj._meta.app_label,
			'name': obj._meta.module_name,
			'pk': obj.pk,
			'__unicode__': unicode(obj),
		}
	
	@classmethod
	def data_serialize_field_value(cls, field, value):
		if field is None:
			#return smart_unicode(value)
			return value
		if isinstance(field.rel, ManyToOneRel):
			if value is not None:
				return cls.data_serialize_model_instance(value)
		elif isinstance(value, FieldFile):
			new_value = {
				'path': value.path,
				'url': value.url,
				'size': value.size,
			}
			if isinstance(value, ImageFieldFile):
				new_value.update({
					'width': value.width,
					'height': value.height,
				})
		else:
			return value
	
	@property
	def sortable_fields(self):
		return [field.name for field in self.model_meta.fields]
	
	@property
	def data_fields(self):
		fields = ['pk', '__unicode__']
		fields.extend(self.data_columns)
		fields.extend(field.name for field in self.model_meta.fields)
		return tuple(set(fields))
	
	@property
	def data_fields_spec(self):
		spec = []
		for field_name in self.data_fields:
			field_spec = {
				'name': field_name,
			}
			if field_name in [field.name for field in self.model_meta.fields if isinstance(field.rel, ManyToOneRel)]:
				field_spec['type'] = 'gilbertmodelforeignkey'
			elif field_name in [field.name for field in self.model_meta.fields if isinstance(field, FileField)]:
				field_spec['type'] = 'gilbertmodelfilefield'
			spec.append(field_spec)
		return spec
	
	@property
	def data_columns_spec(self):
		spec = []
		
		for field_name in self.data_columns:
			column = {
				'dataIndex': field_name,
				'sortable': False,
				'editable': False,
			}
			header, attr = label_for_field(field_name, self.model, model_admin=self, return_attr=True)
			column['header'] = capfirst(header)
			if (field_name in self.sortable_fields) or (getattr(attr, 'admin_order_field', None) in self.sortable_fields):
				column['sortable'] = True
			if field_name in self.data_editable_columns:
				column['editable'] = True
			if field_name in [field.name for field in self.model_meta.fields if isinstance(field.rel, ManyToOneRel)]:
				column['xtype'] = 'foreignkeycolumn'
			spec.append(column)
		return spec
	
	@property
	def data_columns_spec_json(self):
		return json.dumps(self.data_columns_spec)
	
	@property
	def icon_names(self):
		return super(ModelAdmin, self).icon_names + [
			self.icon_name
		]
	
	@ext_method
	def has_permission(self, request):
		return self.has_read_permission(request) or self.has_add_permission(request)
	
	@ext_method
	def has_read_permission(self, request):
		return self.has_change_permission(request)
	
	@ext_method
	def has_add_permission(self, request):
		return request.user.has_perm(self.model_meta.app_label + '.' + self.model_meta.get_add_permission())
	
	@ext_method
	def has_change_permission(self, request):
		return request.user.has_perm(self.model_meta.app_label + '.' + self.model_meta.get_change_permission())
	
	@ext_method
	def has_delete_permission(self, request):
		return request.user.has_perm(self.model_meta.app_label + '.' + self.model_meta.get_delete_permission())
	
	@ext_method
	def all(self, request):
		if not self.has_read_permission(request):
			raise PermissionDenied
		return self.model._default_manager.all()
	
	def queryset(self, request):
		return self.model._default_manager.get_query_set()
	
	@ext_method
	def filter(self, request, **kwargs):
		if not self.has_read_permission(request):
			raise PermissionDenied
		return self.queryset(request).filter(**kwargs)
	
	@ext_method
	def get(self, request, **kwargs):
		if not self.has_read_permission(request):
			raise PermissionDenied
		return self.queryset(request).values().get(**kwargs)
	
	@property
	def form_class(self):
		return modelform_factory(self.model, form=self.form)
	
	@ext_method
	def get_form(self, request, **kwargs):
		if len(kwargs) > 0:
			instance = self.model._default_manager.all().get(**kwargs)
		else:
			if not self.has_add_permission(request):
				raise PermissionDenied
			instance = None
		
		if (instance and not self.has_change_permission(request)) or not self.has_add_permission(request):
			raise PermissionDenied
		
		return self.form_class(instance=instance).as_extdirect()
	
	@ext_method(form_handler=True)
	def save_form(self, request):
		if 'pk' in request.POST:
			try:
				instance = self.model._default_manager.all().get(pk=request.POST['pk'])
			except ObjectDoesNotExist:
				instance = None
		else:
			instance = None
		
		if (instance and not self.has_change_permission(request)) or not self.has_add_permission(request):
			raise PermissionDenied
		
		form = self.form_class(request.POST, request.FILES, instance=instance)
		
		if form.is_valid():
			saved = form.save()
			return True, None, saved.pk
		else:
			return False, form.errors
	
	def data_serialize_object(self, obj):
		row = {}
		for field_name in self.data_fields:
			result = None
			try:
				field, attr, value = lookup_field(field_name, obj, self)
			except (AttributeError, ObjectDoesNotExist):
				pass
			else:
				result = self.data_serialize_field_value(field, value)
			row[field_name] = result
		return row
	
	@property
	def data_metadata(self):
		return {
			'idProperty': 'pk',
			'root': 'root',
			'totalProperty': 'total',
			'successProperty': 'success',
			'fields': self.data_fields_spec,
		}
	
	def data_serialize_queryset(self, queryset, params=None):
		serialized = {
			'metaData': self.data_metadata,
			'root': [],
			'total': queryset.count(),
			'success': True,
		}
		
		if params is not None:
			if 'sort' in params:
				order_by = params['sort']
				if order_by in self.data_fields:
					if order_by not in self.sortable_fields:
						try:
							if hasattr(self, order_by):
								attr = getattr(self, order_by)
							else:
								attr = getattr(self.model, order_by)
							order_by = attr.admin_order_field
						except AttributeError:
							order_by = None
					if order_by is not None:
						if params.get('dir', 'ASC') == 'DESC':
							order_by = '-' + order_by
						serialized['metaData']['sortInfo'] = {
							'field': params['sort'],
							'direction': params.get('dir', 'ASC'),
						}
						queryset = queryset.order_by(order_by)
			if 'start' in params:
				start = params['start']
				serialized['metaData']['start'] = start
				if 'limit' in params:
					limit = params['limit']
					serialized['metaData']['limit'] = limit
					queryset = queryset[start:(start+limit)]
				else:
					queryset = queryset[start:]
		
		for obj in queryset:
			serialized['root'].append(self.data_serialize_object(obj))
		
		return serialized
	
	@ext_method
	def data_read(self, request, **params):
		if not self.has_read_permission(request):
			raise PermissionDenied
		
		queryset = self.model._default_manager.all()
		query = params.pop('query', None)
		filters = params.pop('filters', None)
		
		if filters:
			if isinstance(filters, Q):
				queryset = queryset.filter(filters)
			elif isinstance(filters, dict):
				queryset = queryset.filter(**filters)
			else:
				raise TypeError('Invalid filters parameter')
		
		def construct_search(field_name):
			if field_name.startswith('^'):
				return "%s__istartswith" % field_name[1:]
			elif field_name.startswith('='):
				return "%s__iexact" % field_name[1:]
			elif field_name.startswith('@'):
				return "%s__search" % field_name[1:]
			else:
				return "%s__icontains" % field_name
		
		if self.search_fields and query:
			for word in query.split():
				or_queries = [Q(**{construct_search(str(field_name)): word}) for field_name in self.search_fields]
				queryset = queryset.filter(reduce(operator.or_, or_queries))
			for field_name in self.search_fields:
				if '__' in field_name:
					queryset = queryset.distinct()
					break
		
		return self.data_serialize_queryset(queryset, params)
	
	@ext_method
	def data_create(self, request, **kwargs):
		if not self.has_add_permission(request):
			raise PermissionDenied
		
		return kwargs
	
	@ext_method
	def data_update(self, request, **kwargs):
		if not self.has_change_permission(request):
			raise PermissionDenied
		
		return kwargs
	
	@ext_method
	def data_destroy(self, request, **params):
		if not self.has_delete_permission(request):
			raise PermissionDenied
		
		pks = params['root']
		
		if type(pks) is not list:
			pks = [pks]
		
		for pk in pks:
			if type(pk) is dict:
				pk = pk['pk']
			obj = self.model._default_manager.all().get(pk=pk)
			obj.delete()
		
		return {
			'metaData': self.data_metadata,
			'success': True,
			'root': list(),
		}
	
	@ext_method
	def data_destroy_consequences(self, request, pks):
		if not self.has_delete_permission(request):
			raise PermissionDenied
		
		if type(pks) is not list:
			pks = [pks]
		objs = [self.model._default_manager.all().get(pk=pk) for pk in pks]
		
		using = router.db_for_write(self.model)
		collector = NestedObjects(using=using)
		collector.collect(objs)
		
		return collector.nested(self.data_serialize_model_instance)