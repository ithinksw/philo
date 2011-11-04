from django import forms
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from django.forms.models import ModelForm, BaseInlineFormSet, BaseModelFormSet
from django.forms.formsets import TOTAL_FORM_COUNT
from django.utils.datastructures import SortedDict

from philo.admin.widgets import ModelLookupWidget, EmbedWidget
from philo.models import Contentlet, ContentReference


__all__ = (
	'ContentletForm',
	'ContentletInlineFormSet',
	'ContentReferenceForm',
	'ContentReferenceInlineFormSet'
)


class ContainerForm(ModelForm):
	def __init__(self, *args, **kwargs):
		super(ContainerForm, self).__init__(*args, **kwargs)
		self.verbose_name = self.instance.name.replace('_', ' ')
		self.prefix = self.instance.name


class ContentletForm(ContainerForm):
	content = forms.CharField(required=False, widget=EmbedWidget, label='Content')
	
	def should_delete(self):
		# Delete iff: the data has changed and is now empty.
		return self.has_changed() and not bool(self.cleaned_data['content'])
	
	class Meta:
		model = Contentlet
		fields = ['content']


class ContentReferenceForm(ContainerForm):
	def __init__(self, *args, **kwargs):
		super(ContentReferenceForm, self).__init__(*args, **kwargs)
		try:
			self.fields['content_id'].widget = ModelLookupWidget(self.instance.content_type)
		except ObjectDoesNotExist:
			# This will happen when an empty form (which we will never use) gets instantiated.
			pass
	
	def should_delete(self):
		return self.has_changed() and (self.cleaned_data['content_id'] is None)
	
	class Meta:
		model = ContentReference
		fields = ['content_id']


class ContainerInlineFormSet(BaseInlineFormSet):
	@property
	def containers(self):
		if not hasattr(self, '_containers'):
			self._containers = self.get_containers()
		return self._containers
	
	def total_form_count(self):
		# This ignores the posted management form data... but that doesn't
		# seem to have any ill side effects.
		return len(self.containers.keys())
	
	def _get_initial_forms(self):
		return [form for form in self.forms if form.instance.pk is not None]
	initial_forms = property(_get_initial_forms)
	
	def _get_extra_forms(self):
		return [form for form in self.forms if form.instance.pk is None]
	extra_forms = property(_get_extra_forms)
	
	def _construct_form(self, i, **kwargs):
		if 'instance' not in kwargs:
			kwargs['instance'] = self.containers.values()[i]
		
		# Skip over the BaseModelFormSet. We have our own way of doing things!
		form = super(BaseModelFormSet, self)._construct_form(i, **kwargs)
		
		# Since we skipped over BaseModelFormSet, we need to duplicate what BaseInlineFormSet would do.
		if self.save_as_new:
			# Remove the primary key from the form's data, we are only
			# creating new instances
			form.data[form.add_prefix(self._pk_field.name)] = None
			
			# Remove the foreign key from the form's data
			form.data[form.add_prefix(self.fk.name)] = None
		
		# Set the fk value here so that the form can do it's validation.
		setattr(form.instance, self.fk.get_attname(), self.instance.pk)
		return form
	
	def add_fields(self, form, index):
		"""Override the pk field's initial value with a real one."""
		super(ContainerInlineFormSet, self).add_fields(form, index)
		if index is not None:
			pk_value = self.containers.values()[index].pk
		else:
			pk_value = None
		form.fields[self._pk_field.name].initial = pk_value
	
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
			
			# if the pk_value is None, they have just switched to a
			# template which didn't contain data about this container.
			# Skip!
			if pk_value is not None:
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
	def get_containers(self):
		try:
			containers = self.instance.containers[0]
		except ObjectDoesNotExist:
			containers = []
		
		qs = self.get_queryset().filter(name__in=containers)
		container_dict = SortedDict([(container.name, container) for container in qs])
		for name in containers:
			if name not in container_dict:
				container_dict[name] = self.model(name=name)
		
		container_dict.keyOrder = containers
		return container_dict


class ContentReferenceInlineFormSet(ContainerInlineFormSet):
	def get_containers(self):
		try:
			containers = self.instance.containers[1]
		except ObjectDoesNotExist:
			containers = {}
		
		filter = Q()
		for name, ct in containers.items():
			filter |= Q(name=name, content_type=ct)
		qs = self.get_queryset().filter(filter)
		
		container_dict = SortedDict([(container.name, container) for container in qs])
		
		keyOrder = []
		for name, ct in containers.items():
			keyOrder.append(name)
			if name not in container_dict:
				container_dict[name] = self.model(name=name, content_type=ct)
		
		container_dict.keyOrder = keyOrder
		return container_dict