from django import forms
from django.contrib import admin
from philo.contrib.cowell.fields import ForeignKeyAttribute, ManyToManyAttribute
from philo.contrib.cowell.forms import ProxyFieldForm, proxy_fields_for_entity_model
from philo.contrib.cowell.widgets import ForeignKeyAttributeRawIdWidget, ManyToManyAttributeRawIdWidget
from philo.admin import EntityAdmin


def hide_proxy_fields(hidden, attrs, attname, attvalue, proxy_fields):
	attvalue = set(attvalue)
	proxy_fields = set(proxy_fields)
	if proxy_fields & attvalue:
		hidden[attname] = list(attvalue)
		attrs[attname] = list(attvalue - proxy_fields)


class ProxyFieldAdminMetaclass(EntityAdmin.__metaclass__):
	def __new__(cls, name, bases, attrs):
		# HACK to bypass model validation for proxy fields by masking them as readonly fields
		form = attrs.get('form')
		if form:
			opts = form._meta
			if issubclass(form, ProxyFieldForm) and opts.model:
				proxy_fields = proxy_fields_for_entity_model(opts.model).keys()
				readonly_fields = attrs.pop('readonly_fields', ())
				cls._real_readonly_fields = readonly_fields
				attrs['readonly_fields'] = list(readonly_fields) + proxy_fields
				
				# Additional HACKS to handle raw_id_fields and other attributes that the admin
				# uses model._meta.get_field to validate.
				hidden_attributes = {}
				hide_proxy_fields(hidden_attributes, attrs, 'raw_id_fields', attrs.pop('raw_id_fields', ()), proxy_fields)
				attrs['_hidden_attributes'] = hidden_attributes
		#END HACK
		return EntityAdmin.__metaclass__.__new__(cls, name, bases, attrs)


class ProxyFieldAdmin(EntityAdmin):
	__metaclass__ = ProxyFieldAdminMetaclass
	#form = ProxyFieldForm
	
	def __init__(self, *args, **kwargs):
		# HACK PART 2 restores the actual readonly fields etc. on __init__.
		self.readonly_fields = self.__class__._real_readonly_fields
		if hasattr(self, '_hidden_attributes'):
			for name, value in self._hidden_attributes.items():
				setattr(self, name, value)
		# END HACK
		super(ProxyFieldAdmin, self).__init__(*args, **kwargs)
	
	def formfield_for_dbfield(self, db_field, **kwargs):
		"""
		Override the default behavior to provide special formfields for EntityProxyFields.
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
		return super(ProxyFieldAdmin, self).formfield_for_dbfield(db_field, **kwargs)
	
	def formfield_for_foreignkeyattribute(self, db_field, request=None, **kwargs):
		"""Get a form field for a ForeignKeyAttribute field."""
		db = kwargs.get('using')
		if db_field.name in self.raw_id_fields:
			kwargs['widget'] = ForeignKeyAttributeRawIdWidget(db_field, db)
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
			kwargs['widget'] = ManyToManyAttributeRawIdWidget(db_field, using=db)
			kwargs['help_text'] = ''
		#TODO: Add support for filtered fields.
		#elif db_field.name in (list(self.filter_vertical) + list(self.filter_horizontal)):
		#	kwargs['widget'] = widgets.FilteredSelectMultiple(db_field.verbose_name, (db_field.name in self.filter_vertical))
		
		return db_field.formfield(**kwargs)