from django import forms
from django.conf import settings
from django.contrib.admin.widgets import url_params_from_lookup_dict
from django.utils import simplejson as json
from django.utils.html import escape
from django.utils.safestring import mark_safe
from django.utils.text import truncate_words
from django.utils.translation import ugettext as _


class ModelLookupWidget(forms.TextInput):
	# is_hidden = False
	
	def __init__(self, content_type, attrs=None, limit_choices_to=None):
		self.content_type = content_type
		self.limit_choices_to = limit_choices_to
		super(ModelLookupWidget, self).__init__(attrs)
	
	def render(self, name, value, attrs=None):
		related_url = '../../../%s/%s/' % (self.content_type.app_label, self.content_type.model)
		params = url_params_from_lookup_dict(self.limit_choices_to)
		if params:
			url = u'?' + u'&amp;'.join([u'%s=%s' % (k, v) for k, v in params.items()])
		else:
			url = u''
		if attrs is None:
			attrs = {}
		if "class" not in attrs:
			attrs['class'] = 'vForeignKeyRawIdAdminField'
		output = [super(ModelLookupWidget, self).render(name, value, attrs)]
		output.append('<a href="%s%s" class="related-lookup" id="lookup_id_%s" onclick="return showRelatedObjectLookupPopup(this);">' % (related_url, url, name))
		output.append('<img src="%simg/admin/selector-search.gif" width="16" height="16" alt="%s" />' % (settings.ADMIN_MEDIA_PREFIX, _('Lookup')))
		output.append('</a>')
		if value:
			value_class = self.content_type.model_class()
			try:
				value_object = value_class.objects.get(pk=value)
				output.append('&nbsp;<strong>%s</strong>' % escape(truncate_words(value_object, 14)))
			except value_class.DoesNotExist:
				pass
		return mark_safe(u''.join(output))


class EmbedWidget(forms.Textarea):
	"""A form widget with the HTML class embedding and an embedded list of content-types."""
	def __init__(self, attrs=None):
		from philo.models import value_content_type_limiter
		
		content_types = value_content_type_limiter.classes
		data = []
		
		for content_type in content_types:
			data.append({'app_label': content_type._meta.app_label, 'object_name': content_type._meta.object_name.lower(), 'verbose_name': unicode(content_type._meta.verbose_name)})
		
		json_ = json.dumps(data)
		
		default_attrs = {'class': 'embedding vLargeTextField', 'data-content-types': json_ }
		
		if attrs:
			default_attrs.update(attrs)
			
		super(EmbedWidget, self).__init__(default_attrs)
		
	class Media:
		css = {
			'all': ('philo/css/EmbedWidget.css',),
		}
		js = ('philo/js/EmbedWidget.js',)
