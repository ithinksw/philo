from django import forms
from django.contrib.admin.widgets import AdminTextareaWidget
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from django.forms.models import ModelForm, BaseInlineFormSet
from django.forms.formsets import TOTAL_FORM_COUNT
from philo.admin.widgets import ModelLookupWidget
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