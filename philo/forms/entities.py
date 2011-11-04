from django.forms.models import ModelFormMetaclass, ModelForm, ModelFormOptions
from django.utils.datastructures import SortedDict

from philo.utils import fattr


__all__ = ('EntityForm',)


def proxy_fields_for_entity_model(entity_model, fields=None, exclude=None, widgets=None, formfield_callback=None):
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
		
		if formfield_callback is None:
			formfield = f.formfield(**kwargs)
		elif not callable(formfield_callback):
			raise TypeError('formfield_callback must be a function or callable')
		else:
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


# HACK until http://code.djangoproject.com/ticket/14082 is resolved.
_old = ModelFormMetaclass.__new__
def _new(cls, name, bases, attrs):
	if cls == ModelFormMetaclass:
		m = attrs.get('__metaclass__', None)
		if m is None:
			parents = [b for b in bases if issubclass(b, ModelForm)]
			for c in parents:
				if c.__metaclass__ != ModelFormMetaclass:
					m = c.__metaclass__
					break
	
		if m is not None:
			return m(name, bases, attrs)
	
	return _old(cls, name, bases, attrs)
ModelFormMetaclass.__new__ = staticmethod(_new)
# END HACK


class EntityFormMetaclass(ModelFormMetaclass):
	def __new__(cls, name, bases, attrs):
		try:
			parents = [b for b in bases if issubclass(b, EntityForm)]
		except NameError:
			# We are defining EntityForm itself
			parents = None
		sup = super(EntityFormMetaclass, cls)
		
		if not parents:
			# Then there's no business trying to use proxy fields.
			return sup.__new__(cls, name, bases, attrs)
		
		# Fake a declaration of all proxy fields so they'll be handled correctly.
		opts = ModelFormOptions(attrs.get('Meta', None))
		
		if opts.model:
			formfield_callback = attrs.get('formfield_callback', None)
			proxy_fields = proxy_fields_for_entity_model(opts.model, opts.fields, opts.exclude, opts.widgets, formfield_callback)
		else:
			proxy_fields = {}
		
		new_attrs = proxy_fields.copy()
		new_attrs.update(attrs)
		
		new_class = sup.__new__(cls, name, bases, new_attrs)
		new_class.proxy_fields = proxy_fields
		return new_class


class EntityForm(ModelForm):
	"""
	:class:`EntityForm` knows how to handle :class:`.Entity` instances - specifically, how to set initial values for :class:`.AttributeProxyField`\ s and save cleaned values to an instance on save.
	
	"""
	__metaclass__ = EntityFormMetaclass
	
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
			setattr(instance, f.attname, f.get_storage_value(cleaned_data[f.name]))
		
		if commit:
			instance.save()
			self.save_m2m()
		
		return instance