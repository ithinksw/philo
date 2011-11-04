from django.contrib.contenttypes.generic import BaseGenericInlineFormSet
from django.contrib.contenttypes.models import ContentType
from django.forms.models import ModelForm

from philo.models import Attribute


__all__ = ('AttributeForm', 'AttributeInlineFormSet')


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
		self._cached_value_ct_id = self.instance.value_content_type_id
		self._cached_value = value
		
		# If there is a value, pull in its fields.
		if value is not None:
			self.value_fields = value.value_formfields()
			self.fields.update(self.value_fields)
	
	def save(self, *args, **kwargs):
		# At this point, the cleaned_data has already been stored on self.instance.
		
		if self.instance.value_content_type_id != self._cached_value_ct_id:
			# The value content type has changed. Clear the old value, if there was one.
			if self._cached_value:
				self._cached_value.delete()
			
			# Clear the submitted value, if any.
			self.cleaned_data.pop('value', None)
			
			# Now create a new value instance so that on next instantiation, the form will
			# know what fields to add.
			if self.instance.value_content_type_id is not None:
				self.instance.value = ContentType.objects.get_for_id(self.instance.value_content_type_id).model_class().objects.create()
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