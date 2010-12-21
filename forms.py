from django import forms
from django.contrib.admin.widgets import AdminTextareaWidget
from django.contrib.contenttypes.generic import BaseGenericInlineFormSet
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.db.models import Q
from django.forms.models import model_to_dict, fields_for_model, ModelFormMetaclass, ModelForm, BaseInlineFormSet
from django.forms.formsets import TOTAL_FORM_COUNT
from django.template import loader, loader_tags, TemplateDoesNotExist, Context, Template as DjangoTemplate
from django.utils.datastructures import SortedDict
from philo.admin.widgets import ModelLookupWidget
from philo.models import Entity, Template, Contentlet, ContentReference, Attribute
from philo.utils import fattr


__all__ = ('EntityForm', )


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


class AttributeForm(ModelForm):
	def __init__(self, *args, **kwargs):
		super(AttributeForm, self).__init__(*args, **kwargs)
		
		# This is necessary because model forms store changes to self.instance in their clean method.
		# Mutter mutter.
		self._cached_value_ct = self.instance.value_content_type
		self._cached_value = self.instance.value
		
		if self.instance.value is not None:
			value_field = self.instance.value.value_formfield()
			if value_field:
				self.fields['value'] = value_field
			if hasattr(self.instance.value, 'content_type'):
				self.fields['content_type'] = self.instance.value._meta.get_field('content_type').formfield(initial=getattr(self.instance.value.content_type, 'pk', None))
	
	def save(self, *args, **kwargs):
		# At this point, the cleaned_data has already been stored on self.instance.
		if self.instance.value_content_type != self._cached_value_ct:
			if self.instance.value is not None:
				self._cached_value.delete()
				if 'value' in self.cleaned_data:
					del(self.cleaned_data['value'])
			
			if self.instance.value_content_type is not None:
				# Make a blank value of the new type! Run special code for content_type attributes.
				if hasattr(self.instance.value_content_type.model_class(), 'content_type'):
					if self._cached_value and hasattr(self._cached_value, 'content_type'):
						new_ct = self._cached_value.content_type
					else:
						new_ct = None
					new_value = self.instance.value_content_type.model_class().objects.create(content_type=new_ct)
				else:
					new_value = self.instance.value_content_type.model_class().objects.create()
				
				new_value.apply_data(self.cleaned_data)
				new_value.save()
				self.instance.value = new_value
		else:
			# The value type is the same, but one of the fields has changed.
			# Check to see if the changed value was the content type. We have to check the
			# cleaned_data because self.instance.value.content_type was overridden.
			if hasattr(self.instance.value, 'content_type') and 'content_type' in self.cleaned_data and 'value' in self.cleaned_data and (not hasattr(self._cached_value, 'content_type') or self._cached_value.content_type != self.cleaned_data['content_type']):
				self.cleaned_data['value'] = None
			
			self.instance.value.apply_data(self.cleaned_data)
			self.instance.value.save()
		
		super(AttributeForm, self).save(*args, **kwargs)
		return self.instance
	
	class Meta:
		model = Attribute


class AttributeInlineFormSet(BaseGenericInlineFormSet):
	"Necessary to force the GenericInlineFormset to use the form's save method for new objects."
	def save_new(self, form, commit):
		setattr(form.instance, self.ct_field.get_attname(), ContentType.objects.get_for_model(self.instance).pk)
		setattr(form.instance, self.ct_fk_field.get_attname(), self.instance.pk)
		return form.save()


class ContainerForm(ModelForm):
	def __init__(self, *args, **kwargs):
		super(ContainerForm, self).__init__(*args, **kwargs)
		self.verbose_name = self.instance.name.replace('_', ' ')


class ContentletForm(ContainerForm):
	content = forms.CharField(required=False, widget=AdminTextareaWidget, label='Content')
	
	def should_delete(self):
		return not bool(self.cleaned_data['content'])
	
	class Meta:
		model = Contentlet
		fields = ['name', 'content']


class ContentReferenceForm(ContainerForm):
	def __init__(self, *args, **kwargs):
		super(ContentReferenceForm, self).__init__(*args, **kwargs)
		try:
			self.fields['content_id'].widget = ModelLookupWidget(self.instance.content_type)
		except ObjectDoesNotExist:
			# This will happen when an empty form (which we will never use) gets instantiated.
			pass
	
	def should_delete(self):
		return (self.cleaned_data['content_id'] is None)
	
	class Meta:
		model = ContentReference
		fields = ['name', 'content_id']


class ContainerInlineFormSet(BaseInlineFormSet):
	def __init__(self, containers, data=None, files=None, instance=None, save_as_new=False, prefix=None, queryset=None):
		# Unfortunately, I need to add some things to BaseInline between its __init__ and its
		# super call, so a lot of this is repetition.
		
		# Start cribbed from BaseInline
		from django.db.models.fields.related import RelatedObject
		self.save_as_new = save_as_new
		# is there a better way to get the object descriptor?
		self.rel_name = RelatedObject(self.fk.rel.to, self.model, self.fk).get_accessor_name()
		if self.fk.rel.field_name == self.fk.rel.to._meta.pk.name:
			backlink_value = self.instance
		else:
			backlink_value = getattr(self.instance, self.fk.rel.field_name)
		if queryset is None:
			queryset = self.model._default_manager
		qs = queryset.filter(**{self.fk.name: backlink_value})
		# End cribbed from BaseInline
		
		self.container_instances, qs = self.get_container_instances(containers, qs)
		self.extra_containers = containers
		self.extra = len(self.extra_containers)
		super(BaseInlineFormSet, self).__init__(data, files, prefix=prefix, queryset=qs)
	
	def get_container_instances(self, containers, qs):
		raise NotImplementedError
	
	def total_form_count(self):
		if self.data or self.files:
			return self.management_form.cleaned_data[TOTAL_FORM_COUNT]
		else:
			return self.initial_form_count() + self.extra
	
	def save_existing_objects(self, commit=True):
		self.changed_objects = []
		self.deleted_objects = []
		if not self.get_queryset():
			return []

		saved_instances = []
		for form in self.initial_forms:
			pk_name = self._pk_field.name
			raw_pk_value = form._raw_value(pk_name)

			# clean() for different types of PK fields can sometimes return
			# the model instance, and sometimes the PK. Handle either.
			pk_value = form.fields[pk_name].clean(raw_pk_value)
			pk_value = getattr(pk_value, 'pk', pk_value)

			obj = self._existing_object(pk_value)
			if form.should_delete():
				self.deleted_objects.append(obj)
				obj.delete()
				continue
			if form.has_changed():
				self.changed_objects.append((obj, form.changed_data))
				saved_instances.append(self.save_existing(form, obj, commit=commit))
				if not commit:
					self.saved_forms.append(form)
		return saved_instances

	def save_new_objects(self, commit=True):
		self.new_objects = []
		for form in self.extra_forms:
			if not form.has_changed():
				continue
			# If someone has marked an add form for deletion, don't save the
			# object.
			if form.should_delete():
				continue
			self.new_objects.append(self.save_new(form, commit=commit))
			if not commit:
				self.saved_forms.append(form)
		return self.new_objects


class ContentletInlineFormSet(ContainerInlineFormSet):
	def __init__(self, data=None, files=None, instance=None, save_as_new=False, prefix=None, queryset=None):
		if instance is None:
			self.instance = self.fk.rel.to()
		else:
			self.instance = instance
		
		try:
			containers = list(self.instance.containers[0])
		except ObjectDoesNotExist:
			containers = []
	
		super(ContentletInlineFormSet, self).__init__(containers, data, files, instance, save_as_new, prefix, queryset)
	
	def get_container_instances(self, containers, qs):
		qs = qs.filter(name__in=containers)
		container_instances = []
		for container in qs:
			container_instances.append(container)
			containers.remove(container.name)
		return container_instances, qs
	
	def _construct_form(self, i, **kwargs):
		if i >= self.initial_form_count(): # and not kwargs.get('instance'):
			kwargs['instance'] = self.model(name=self.extra_containers[i - self.initial_form_count() - 1])
		
		return super(ContentletInlineFormSet, self)._construct_form(i, **kwargs)


class ContentReferenceInlineFormSet(ContainerInlineFormSet):
	def __init__(self, data=None, files=None, instance=None, save_as_new=False, prefix=None, queryset=None):
		if instance is None:
			self.instance = self.fk.rel.to()
		else:
			self.instance = instance
		
		try:
			containers = list(self.instance.containers[1])
		except ObjectDoesNotExist:
			containers = []
	
		super(ContentReferenceInlineFormSet, self).__init__(containers, data, files, instance, save_as_new, prefix, queryset)
	
	def get_container_instances(self, containers, qs):
		filter = Q()
		
		for name, ct in containers:
			filter |= Q(name=name, content_type=ct)
		
		qs = qs.filter(filter)
		container_instances = []
		for container in qs:
			container_instances.append(container)
			containers.remove((container.name, container.content_type))
		return container_instances, qs

	def _construct_form(self, i, **kwargs):
		if i >= self.initial_form_count(): # and not kwargs.get('instance'):
			name, content_type = self.extra_containers[i - self.initial_form_count() - 1]
			kwargs['instance'] = self.model(name=name, content_type=content_type)

		return super(ContentReferenceInlineFormSet, self)._construct_form(i, **kwargs)