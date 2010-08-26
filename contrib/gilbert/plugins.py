from inspect import isclass, getargspec
from functools import wraps
from django.utils.encoding import force_unicode
from django.forms.widgets import Widget, Input, HiddenInput, FileInput, DateInput, TimeInput, Textarea, CheckboxInput, Select, SelectMultiple
from django.forms.fields import FileField
from django.forms.forms import BaseForm


def _render_ext(self, name, value):
	ext_spec = {'name': name}
	if value is not None:
		ext_spec['value'] = value
	if isinstance(self, Input):
		if isinstance(self, HiddenInput):
			ext_spec['xtype'] = 'hidden'
		elif isinstance(self, FileInput):
			ext_spec['xtype'] = 'fileuploadfield'
		elif isinstance(self, DateInput):
			ext_spec['xtype'] = 'datefield'
		elif isinstance(self, TimeInput):
			ext_spec['xtype'] = 'timefield'
		else:
			ext_spec['xtype'] = 'textfield'
			ext_spec['inputType'] = self.input_type
	elif isinstance(self, Textarea):
		ext_spec['xtype'] = 'textarea'
	elif isinstance(self, CheckboxInput):
		ext_spec['xtype'] = 'checkbox'
	elif isinstance(self, Select):
		ext_spec['xtype'] = 'combo'
		ext_spec['store'] = self.choices
		ext_spec['typeAhead'] = True
		if isinstance(self, SelectMultiple):
			pass
	if ext_spec:
		return ext_spec
	return None


Widget.render_ext = _render_ext


def _as_ext(self):
	ext_spec = {}
	
	fields = []
	for bf in self:
		if bf.label:
			label = force_unicode(bf.label)
		else:
			label = ''
		
		if bf.field.show_hidden_initial:
			only_initial = True
		else:
			only_initial = False
		
		widget = bf.field.widget
		
		if not self.is_bound:
			data = self.initial.get(bf.name, bf.field.initial)
			if callable(data):
				data = data()
		else:
			if isinstance(bf.field, FileField) and bf.data is None:
				data = self.initial.get(bf.name, bf.field.initial)
			else:
				data = bf.data
		if not only_initial:
			name = bf.html_name
		else:
			name = bf.html_initial_name
		
		rendered = widget.render_ext(name, data)
		if rendered is not None:
			rendered['fieldLabel'] = label
			fields.append(rendered)
	ext_spec['items'] = fields
	ext_spec['labelSeparator'] = self.label_suffix
	return ext_spec


BaseForm.as_ext = _as_ext


def is_gilbert_method(function):
	return getattr(function, 'gilbert_method', False)


def gilbert_method(function=None, name=None, argc=None, form_handler=False, restricted=True):
	def setter(function):
		setattr(function, 'gilbert_method', True)
		setattr(function, 'name', name or function.__name__)
		setattr(function, 'form_handler', form_handler)
		setattr(function, 'restricted', restricted)
		new_argc = argc
		if new_argc is None:
			args = getargspec(function)[0]
			new_argc = len(args)
			if new_argc > 0:
				if args[0] == 'self':
					args = args[1:]
					new_argc = new_argc - 1
				if new_argc > 0:
					if args[0] == 'request':
						args = args[1:]
						new_argc = new_argc - 1
		setattr(function, 'argc', new_argc)
		return function
	if function is not None:
		return setter(function)
	return setter


class GilbertPluginBase(type):
	def __new__(cls, name, bases, attrs):
		if 'methods' not in attrs:
			methods = []
			for attr in attrs.values():
				if is_gilbert_method(attr):
					methods.append(attr.name)
			attrs['methods'] = methods
		return super(GilbertPluginBase, cls).__new__(cls, name, bases, attrs)


class GilbertPlugin(object):
	__metaclass__ = GilbertPluginBase
	
	def __init__(self, site):
		self.site = site
	
	def get_method(self, method_name):
		method = getattr(self, method_name, None)
		if not is_gilbert_method(method):
			return None
		return method
	
	@property
	def urls(self):
		return []
	
	@property
	def js(self):
		return []
	
	@property
	def css(self):
		return []
	
	@property
	def fugue_icons(self):
		return []


class GilbertModelAdmin(GilbertPlugin):
	def __init__(self, site, model):
		self.model = model
		self.name = model._meta.object_name
		super(GilbertModelAdmin, self).__init__(site)
	
	@gilbert_method
	def all(self):
		return list(self.model._default_manager.all().values())
	
	@gilbert_method
	def get(self, constraint):
		return self.model._default_manager.all().values().get(**constraint)