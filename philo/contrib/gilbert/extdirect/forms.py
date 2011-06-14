import os.path
from django.forms.widgets import Widget, TextInput, PasswordInput, HiddenInput, MultipleHiddenInput, FileInput, Textarea, DateInput, DateTimeInput, TimeInput, CheckboxInput, Select, NullBooleanSelect, SelectMultiple, RadioSelect, CheckboxSelectMultiple, MultiWidget, SplitHiddenDateTimeWidget
from django.forms.forms import BaseForm, BoundField
from django.forms.fields import FileField
from django.forms.models import ModelForm, ModelChoiceField, ModelMultipleChoiceField
from django.db.models import ForeignKey, ManyToManyField, Q
from django.utils.encoding import force_unicode
from philo.utils import ContentTypeLimiter
from philo.hacks import Category


# The "categories" in this module are listed in reverse order, because I wasn't able to ensure that they'd all take effect otherwise...


#still to do: SplitHiddenDateTimeWidget


class MultiWidget(MultiWidget):
	__metaclass__ = Category
	
	def render_extdirect(self, name, data):
		if not isinstance(data, list):
			data = self.decompress(data)
		
		specs = []
		for i, widget in enumerate(self.widgets):
			try:
				widget_data = data[i]
			except IndexError:
				widget_data = None
			specs.extend(widget.render_extdirect(name + '_%s' % i, widget_data))
		return specs


#still to do: RadioSelect, CheckboxSelectMultiple


class SelectMultiple(SelectMultiple):
	__metaclass__ = Category
	extdirect_xtype = 'superboxselect'
	
	def render_extdirect(self, name, data):
		if self.choices:
			store = [choice for choice in self.choices if choice[0]]
		else:
			store = []
		spec = {
			'name': name,
			'value': data,
			'store': store,
			'xtype': self.extdirect_xtype,
			'forceFormValue': False
		}
		if not spec['value']:
			del spec['value']
		return [spec]


class NullBooleanSelect(NullBooleanSelect):
	__metaclass__ = Category
	
	def render_extdirect(self, name, data):
		try:
			data = {True: u'2', False: u'3', u'2': u'2', u'3': u'3'}[data]
		except KeyError:
			data = u'1'
		return super(NullBooleanSelect, self).render_extdirect(name, data)


class Select(Select):
	__metaclass__ = Category
	extdirect_xtype = 'combo'
	
	def render_extdirect(self, name, data):
		if self.choices:
			store = [choice for choice in self.choices if choice[0]]
		else:
			store = []
		spec = {
			'hiddenName': name,
			'hiddenValue': data,
			'value': data,
			'xtype': self.extdirect_xtype,
			'store': store,
			'editable': False,
			'disableKeyFilter': True,
			'forceSelection': True,
			'triggerAction': 'all',
		}
		if not spec['value']:
			del spec['value']
		return [spec]


class CheckboxInput(CheckboxInput):
	__metaclass__ = Category
	extdirect_xtype = 'checkbox'
	
	def render_extdirect(self, name, data):
		data = bool(data)
		specs = super(CheckboxInput, self).render_extdirect(name, data)
		specs[0]['checked'] = data
		return specs


class DateTimeInput(DateTimeInput):
	__metaclass__ = Category
	extdirect_xtype = 'gilbertdatetimefield'


class TimeInput(TimeInput):
	__metaclass__ = Category
	extdirect_xtype = 'timefield'


class DateInput(DateInput):
	__metaclass__ = Category
	extdirect_xtype = 'datefield'


class Textarea(Textarea):
	__metaclass__ = Category
	extdirect_xtype = 'textarea'


class FileInput(FileInput):
	__metaclass__ = Category
	extdirect_xtype = 'fileuploadfield'
	
	def render_extdirect(self, name, data):
		if data is not None:
			data = os.path.split(data.name)[1]
		return super(FileInput, self).render_extdirect(name, data)


class MultipleHiddenInput(MultipleHiddenInput):
	__metaclass__ = Category
	extdirect_xtype = 'hidden'
	
	def render_extdirect(self, name, data):
		if data is None:
			data = []
		return [specs.extend(super(MultipleHiddenInput, self).render_extdirect(name, data)) for datum in data]


class HiddenInput(HiddenInput):
	__metaclass__ = Category
	extdirect_xtype = 'hidden'


class PasswordInput(PasswordInput):
	__metaclass__ = Category
	extdirect_xtype = 'textfield'
	
	def render_extdirect(self, name, data):
		specs = super(PasswordInput, self).render_extdirect(name, data)
		specs[0]['inputType'] = self.input_type
		return specs


class TextInput(TextInput):
	__metaclass__ = Category
	extdirect_xtype = 'textfield'


class Widget(Widget):
	__metaclass__ = Category
	extdirect_xtype = None
	
	def render_extdirect(self, name, data):
		if not self.extdirect_xtype:
			raise NotImplementedError
		spec = {
			'name': name,
			'value': data,
			'xtype': self.extdirect_xtype
		}
		if not spec['value']:
			del spec['value']
		return [spec]


class BoundField(BoundField):
	__metaclass__ = Category
	
	def as_hidden_extdirect(self, only_initial=False):
		return self.as_widget_extdirect(self.field.hidden_widget(), only_initial)
	
	def as_widget_extdirect(self, widget=None, only_initial=False):
		if not widget:
			widget = self.field.widget
			standard_widget = True
		else:
			standard_widget = False
		
		if not self.form.is_bound:
			data = self.form.initial.get(self.name, self.field.initial)
			if callable(data):
				data = data()
		else:
			if isinstance(self.field, FileField) and self.data is None:
				data = self.form.initial.get(self.name, self.field.initial)
			else:
				data = self.data
		data = self.field.prepare_value(data)
		
		if not only_initial:
			name = self.html_name
		else:
			name = self.html_initial_name
		
		specs = widget.render_extdirect(name, data)
		
		if standard_widget and isinstance(self.field, ModelChoiceField):
			limit_choices_to = None
			
			if isinstance(self.form, ModelForm):
				model = self.form._meta.model
				model_fields = model._meta.fields + model._meta.many_to_many
				
				for model_field in model_fields:
					if model_field.name == self.name and (isinstance(model_field, ForeignKey) or isinstance(model_field, ManyToManyField)):
						limit_choices_to = model_field.rel.limit_choices_to
						if limit_choices_to is None:
							limit_choices_to = {}
						elif isinstance(limit_choices_to, ContentTypeLimiter):
							limit_choices_to = limit_choices_to.q_object()
						elif not isinstance(limit_choices_to, dict):
							limit_choices_to = None # can't support other objects with add_to_query methods
						break
			
			if limit_choices_to is not None:
				specs[0]['model_filters'] = limit_choices_to
			else:
				specs[0]['model_filters'] = {
					'pk__in': self.field.queryset.values_list('pk', flat=True)
				}
				
			specs[0]['model_app_label'] = self.field.queryset.model._meta.app_label
			specs[0]['model_name'] = self.field.queryset.model._meta.object_name
			
			if isinstance(self.field, ModelMultipleChoiceField):
				specs[0]['xtype'] = 'gilbertmodelmultiplechoicefield'
			else:
				specs[0]['xtype'] = 'gilbertmodelchoicefield'
				specs[0]['backup_store'] = specs[0]['store']
				del specs[0]['store']
		
		return specs
			
	def as_extdirect(self):
		if self.field.show_hidden_initial:
			return self.as_widget_extdirect() + self.as_hidden_extdirect(only_initial=True)
		return self.as_widget_extdirect()


class BaseForm(BaseForm):
	__metaclass__ = Category
	
	def as_extdirect(self):
		fields = []
		
		for bound_field in self:
			if bound_field.label:
				label = bound_field.label
			else:
				label = ''
			
			if bound_field.field.help_text:
				help_text = bound_field.field.help_text
			else:
				help_text = ''
			
			specs = bound_field.as_extdirect()
			
			if len(specs) < 1:
				continue
			
			if len(specs) > 1:
				specs = [{
					'xtype': 'compositefield',
					'items': specs
				}]
			
			if label:
				specs[0]['fieldLabel'] = label
			if help_text:
				specs[0]['help_text'] = help_text
			
			fields.extend(specs)
		
		if isinstance(self, ModelForm):
			pk = self.instance.pk
			if pk is not None:
				fields.append({
					'name': 'pk',
					'value': pk,
					'xtype': 'hidden'
				})
		
		return {
			'items': fields,
			'labelSeparator': self.label_suffix,
			'fileUpload': self.is_multipart()
		}