from django import forms
from django.contrib.contenttypes.generic import BaseGenericInlineFormSet
from django.contrib.contenttypes.models import ContentType
from django.forms.models import ModelFormMetaclass, ModelForm
from django.utils.datastructures import SortedDict
from philo.models import Attribute
from philo.utils import fattr


__all__ = ('EntityForm', 'AttributeForm', 'AttributeInlineFormSet')


def proxy_fields_for_entity_model(entity_model, fields=None, exclude=None, widgets=None, formfield_callback=lambda f, **kwargs: f.formfield(**kwargs)):
	field_list = []
	ignored = []
	opts = entity_model._entity_meta
	for f in opts.proxy_fields:
		if not f.editable:
			continue
		if fields and not f.name in fields:
			continue
		if exclude and f.name in exclude:
			continue
		if widgets and f.name in widgets:
			kwargs = {'widget': widgets[f.name]}
		else:
			kwargs = {}
		formfield = formfield_callback(f, **kwargs)
		if formfield:
			field_list.append((f.name, formfield))
		else:
			ignored.append(f.name)
	field_dict = SortedDict(field_list)
	if fields:
		field_dict = SortedDict(
			[(f, field_dict.get(f)) for f in fields
				if ((not exclude) or (exclude and f not in exclude)) and (f not in ignored) and (f in field_dict)]
		)
	return field_dict


# BEGIN HACK - This will not be required after http://code.djangoproject.com/ticket/14082 has been resolved

class EntityFormBase(ModelForm):
	pass

_old_metaclass_new = ModelFormMetaclass.__new__

def _new_metaclass_new(cls, name, bases, attrs):
	new_class = _old_metaclass_new(cls, name, bases, attrs)
	if issubclass(new_class, EntityFormBase) and new_class._meta.model:
		new_class.base_fields.update(proxy_fields_for_entity_model(new_class._meta.model, new_class._meta.fields, new_class._meta.exclude, new_class._meta.widgets)) # don't pass in formfield_callback
	return new_class

ModelFormMetaclass.__new__ = staticmethod(_new_metaclass_new)

# END HACK


class EntityForm(EntityFormBase): # Would inherit from ModelForm directly if it weren't for the above HACK
	def __init__(self, *args, **kwargs):
		initial = kwargs.pop('initial', None)
		instance = kwargs.get('instance', None)
		if instance is not None:
			new_initial = {}
			for f in instance._entity_meta.proxy_fields:
				if self._meta.fields and not f.name in self._meta.fields:
					continue
				if self._meta.exclude and f.name in self._meta.exclude:
					continue
				new_initial[f.name] = f.value_from_object(instance)
		else:
			new_initial = {}
		if initial is not None:
			new_initial.update(initial)
		kwargs['initial'] = new_initial
		super(EntityForm, self).__init__(*args, **kwargs)
	
	@fattr(alters_data=True)
	def save(self, commit=True):
		cleaned_data = self.cleaned_data
		instance = super(EntityForm, self).save(commit=False)
		
		for f in instance._entity_meta.proxy_fields:
			if not f.editable or not f.name in cleaned_data:
				continue
			if self._meta.fields and f.name not in self._meta.fields:
				continue
			if self._meta.exclude and f.name in self._meta.exclude:
				continue
			setattr(instance, f.attname, cleaned_data[f.name])
		
		if commit:
			instance.save()
			self.save_m2m()
		
		return instance

	
	def apply_data(self, cleaned_data):
		self.value = cleaned_data.get('value', None)
	
	def apply_data(self, cleaned_data):
		if 'value' in cleaned_data and cleaned_data['value'] is not None:
			self.value = cleaned_data['value']
		else:
			self.content_type = cleaned_data.get('content_type', None)
			# If there is no value set in the cleaned data, clear the stored value.
			self.object_id = None
	
	def apply_data(self, cleaned_data):
		if 'value' in cleaned_data and cleaned_data['value'] is not None:
			self.value = cleaned_data['value']
		else:
			self.content_type = cleaned_data.get('content_type', None)
			# If there is no value set in the cleaned data, clear the stored value.
			self.value = []

class AttributeForm(ModelForm):
	"""
	This class handles an attribute's fields as well as the fields for its value (if there is one.)
	The fields defined will vary depending on the value type, but the fields for defining the value
	(i.e. value_content_type and value_object_id) will always be defined. Except that value_object_id
	will never be defined. BLARGH!
	"""
	def __init__(self, *args, **kwargs):
		super(AttributeForm, self).__init__(*args, **kwargs)
		
		# This is necessary because model forms store changes to self.instance in their clean method.
		# Mutter mutter.
		value = self.instance.value
		self._cached_value_ct = self.instance.value_content_type
		self._cached_value = value
		
		# If there is a value, pull in its fields.
		if value is not None:
			self.value_fields = value.value_formfields()
			self.fields.update(self.value_fields)
	
	def save(self, *args, **kwargs):
		# At this point, the cleaned_data has already been stored on self.instance.
		
		if self.instance.value_content_type != self._cached_value_ct:
			# The value content type has changed. Clear the old value, if there was one.
			if self._cached_value:
				self._cached_value.delete()
			
			# Clear the submitted value, if any.
			self.cleaned_data.pop('value', None)
			
			# Now create a new value instance so that on next instantiation, the form will
			# know what fields to add.
			if self.instance.value_content_type is not None:
				self.instance.value = self.instance.value_content_type.model_class().objects.create()
		elif self.instance.value is not None:
			# The value content type is the same, but one of the value fields has changed.
			
			# Use construct_instance to apply the changes from the cleaned_data to the value instance.
			fields = self.value_fields.keys()
			if set(fields) & set(self.changed_data):
				self.instance.value.construct_instance(**dict([(key, self.cleaned_data[key]) for key in fields]))
				self.instance.value.save()
		
		return super(AttributeForm, self).save(*args, **kwargs)
	
	class Meta:
		model = Attribute


class AttributeInlineFormSet(BaseGenericInlineFormSet):
	"Necessary to force the GenericInlineFormset to use the form's save method for new objects."
	def save_new(self, form, commit):
		setattr(form.instance, self.ct_field.get_attname(), ContentType.objects.get_for_model(self.instance).pk)
		setattr(form.instance, self.ct_fk_field.get_attname(), self.instance.pk)
		return form.save()