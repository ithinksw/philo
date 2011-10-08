from django.conf import settings
from django.contrib import admin
from django.contrib.contenttypes import generic
from django.http import HttpResponse
from django.utils import simplejson as json
from django.utils.html import escape
from mptt.admin import MPTTModelAdmin

from philo.models import Attribute
from philo.models.fields.entities import ForeignKeyAttribute, ManyToManyAttribute
from philo.admin.forms.attributes import AttributeForm, AttributeInlineFormSet
from philo.forms.entities import EntityForm, proxy_fields_for_entity_model


COLLAPSE_CLASSES = ('collapse', 'collapse-closed', 'closed',)


class AttributeInline(generic.GenericTabularInline):
	ct_field = 'entity_content_type'
	ct_fk_field = 'entity_object_id'
	model = Attribute
	extra = 1
	allow_add = True
	classes = COLLAPSE_CLASSES
	form = AttributeForm
	formset = AttributeInlineFormSet
	fields = ['key', 'value_content_type']
	if 'grappelli' in settings.INSTALLED_APPS:
		template = 'admin/philo/edit_inline/grappelli_tabular_attribute.html'
	else:
		template = 'admin/philo/edit_inline/tabular_attribute.html'


# HACK to bypass model validation for proxy fields
class SpoofedHiddenFields(object):
	def __init__(self, proxy_fields, value):
		self.value = value
		self.spoofed = list(set(value) - set(proxy_fields))
	
	def __get__(self, instance, owner):
		if instance is None:
			return self.spoofed
		return self.value


class SpoofedAddedFields(SpoofedHiddenFields):
	def __init__(self, proxy_fields, value):
		self.value = value
		self.spoofed = list(set(value) | set(proxy_fields))


def hide_proxy_fields(cls, attname):
	val = getattr(cls, attname, [])
	proxy_fields = getattr(cls, 'proxy_fields')
	if val:
		setattr(cls, attname, SpoofedHiddenFields(proxy_fields, val))

def add_proxy_fields(cls, attname):
	val = getattr(cls, attname, [])
	proxy_fields = getattr(cls, 'proxy_fields')
	setattr(cls, attname, SpoofedAddedFields(proxy_fields, val))


class EntityAdminMetaclass(admin.ModelAdmin.__metaclass__):
	def __new__(cls, name, bases, attrs):
		new_class = super(EntityAdminMetaclass, cls).__new__(cls, name, bases, attrs)
		hide_proxy_fields(new_class, 'raw_id_fields')
		add_proxy_fields(new_class, 'readonly_fields')
		return new_class
# END HACK

class EntityAdmin(admin.ModelAdmin):
	__metaclass__ = EntityAdminMetaclass
	form = EntityForm
	inlines = [AttributeInline]
	save_on_top = True
	proxy_fields = []
	
	def formfield_for_dbfield(self, db_field, **kwargs):
		"""
		Override the default behavior to provide special formfields for EntityEntitys.
		Essentially clones the ForeignKey/ManyToManyField special behavior for the Attribute versions.
		"""
		if not db_field.choices and isinstance(db_field, (ForeignKeyAttribute, ManyToManyAttribute)):
			request = kwargs.pop("request", None)
			# Combine the field kwargs with any options for formfield_overrides.
			# Make sure the passed in **kwargs override anything in
			# formfield_overrides because **kwargs is more specific, and should
			# always win.
			if db_field.__class__ in self.formfield_overrides:
				kwargs = dict(self.formfield_overrides[db_field.__class__], **kwargs)
			
			# Get the correct formfield.
			if isinstance(db_field, ManyToManyAttribute):
				formfield = self.formfield_for_manytomanyattribute(db_field, request, **kwargs)
			elif isinstance(db_field, ForeignKeyAttribute):
				formfield = self.formfield_for_foreignkeyattribute(db_field, request, **kwargs)
			
			# For non-raw_id fields, wrap the widget with a wrapper that adds
			# extra HTML -- the "add other" interface -- to the end of the
			# rendered output. formfield can be None if it came from a
			# OneToOneField with parent_link=True or a M2M intermediary.
			# TODO: Implement this.
			#if formfield and db_field.name not in self.raw_id_fields:
			#	formfield.widget = admin.widgets.RelatedFieldWidgetWrapper(formfield.widget, db_field, self.admin_site)
			
			return formfield
		return super(EntityAdmin, self).formfield_for_dbfield(db_field, **kwargs)
	
	def formfield_for_foreignkeyattribute(self, db_field, request=None, **kwargs):
		"""Get a form field for a ForeignKeyAttribute field."""
		db = kwargs.get('using')
		if db_field.name in self.raw_id_fields:
			kwargs['widget'] = admin.widgets.ForeignKeyRawIdWidget(db_field, db)
		#TODO: Add support for radio fields
		#elif db_field.name in self.radio_fields:
		#	kwargs['widget'] = widgets.AdminRadioSelect(attrs={
		#		'class': get_ul_class(self.radio_fields[db_field.name]),
		#	})
		#	kwargs['empty_label'] = db_field.blank and _('None') or None
		
		return db_field.formfield(**kwargs)
	
	def formfield_for_manytomanyattribute(self, db_field, request=None, **kwargs):
		"""Get a form field for a ManyToManyAttribute field."""
		db = kwargs.get('using')
		
		if db_field.name in self.raw_id_fields:
			kwargs['widget'] = admin.widgets.ManyToManyRawIdWidget(db_field, using=db)
			kwargs['help_text'] = ''
		#TODO: Add support for filtered fields.
		#elif db_field.name in (list(self.filter_vertical) + list(self.filter_horizontal)):
		#	kwargs['widget'] = widgets.FilteredSelectMultiple(db_field.verbose_name, (db_field.name in self.filter_vertical))
		
		return db_field.formfield(**kwargs)


class TreeEntityAdmin(EntityAdmin, MPTTModelAdmin):
	pass