from django.core.exceptions import ValidationError
from django.forms.models import model_to_dict, fields_for_model, ModelFormMetaclass, ModelForm
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