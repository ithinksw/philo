from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.forms.models import model_to_dict, fields_for_model, ModelFormMetaclass, ModelForm, BaseInlineFormSet
from django.template import loader, loader_tags, TemplateDoesNotExist, Context, Template as DjangoTemplate
from django.utils.datastructures import SortedDict
from philo.models import Entity, Template
from philo.models.fields import RelationshipField
from philo.utils import fattr


__all__ = ('EntityForm', )


def proxy_fields_for_entity_model(entity_model, fields=None, exclude=None, widgets=None, formfield_callback=lambda f, **kwargs: f.formfield(**kwargs)):
	field_list = []
	ignored = []
	opts = entity_model._entity_meta
	for f in opts.proxy_fields:
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
			if self._meta.fields and f.name not in self._meta.fields:
				continue
			setattr(instance, f.attname, cleaned_data[f.name])
		
		if commit:
			instance.save()
			self.save_m2m()
		
		return instance


def validate_template(template):
	"""
	Makes sure that the template and all included or extended templates are valid.
	""" 
	for node in template.nodelist:
		try:
			if isinstance(node, loader_tags.ExtendsNode):
				extended_template = node.get_parent(Context())
				validate_template(extended_template)
			elif isinstance(node, loader_tags.IncludeNode):
				included_template = loader.get_template(node.template_name.resolve(Context()))
				validate_template(extended_template)
		except Exception, e:
			raise ValidationError("Template code invalid. Error was: %s: %s" % (e.__class__.__name__, e))


class TemplateForm(ModelForm):
	def clean_code(self):
		code = self.cleaned_data['code']
		try:
			t = DjangoTemplate(code)
		except Exception, e:
			raise ValidationError("Template code invalid. Error was: %s: %s" % (e.__class__.__name__, e))

		validate_template(t)
		return code

	class Meta:
		model = Template


class ContainerInlineFormSet(BaseInlineFormSet):
	def __init__(self, containers, data=None, files=None, instance=None, save_as_new=False, prefix=None, queryset=None):
		# Unfortunately, I need to add some things to BaseInline between its __init__ and its super call, so
		# a lot of this is repetition.
		
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
		qs = queryset.filter(**{self.fk.name: backlink_value}).filter(name__in=containers)
		# End cribbed from BaseInline
		
		self.container_instances = []
		for container in qs:
			self.container_instances.append(container)
			containers.remove(container.name)
		self.extra_containers = containers
		self.extra = len(self.extra_containers)
		
		super(BaseInlineFormSet, self).__init__(data, files, prefix, qs)
	
	def _construct_form(self, i, **kwargs):
		if i > self.initial_form_count(): # and not kwargs.get('instance'):
			kwargs['instance'] = self.model(name=self.extra_containers[i - self.initial_form_count() - 1])
		
		return super(ContainerInlineFormSet, self)._construct_form(i, **kwargs)


class ContentletInlineFormSet(ContainerInlineFormSet):
	def __init__(self, data=None, files=None, instance=None, save_as_new=False, prefix=None, queryset=None):
		if instance is None:
			self.instance = self.fk.rel.to()
			containers = []
		else:
			self.instance = instance
			containers = list(self.instance.containers[0])
	
		super(ContentletInlineFormSet, self).__init__(containers, data, files, instance, save_as_new, prefix, queryset)	


class ContentReferenceInlineFormSet(ContainerInlineFormSet):
	def __init__(self, data=None, files=None, instance=None, save_as_new=False, prefix=None, queryset=None):
		if instance is None:
			self.instance = self.fk.rel.to()
			containers = []
		else:
			self.instance = instance
			containers = list(self.instance.containers[1])
	
		super(ContentReferenceInlineFormSet, self).__init__(containers, data, files, instance, save_as_new, prefix, queryset)