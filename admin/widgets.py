from django import forms
from django.conf import settings


class ModelLookupWidget(forms.TextInput):
	# is_hidden = False
	
	def __init__(self, content_type, attrs=None):
		self.content_type = content_type
		super(ModelLookupWidget, self).__init__(attrs)
	
	def render(self, name, value, attrs=None):
		related_url = '../../../%s/%s/' % (self.content_type.app_label, self.content_type.model)
		if attrs is None:
			attrs = {}
		if not attrs.has_key('class'):
			attrs['class'] = 'vForeignKeyRawIdAdminField'
		output = super(ModelLookupWidget, self).render(name, value, attrs)
		output += '<a href="%s" class="related-lookup" id="lookup_id_%s" onclick="return showRelatedObjectLookupPopup(this);">' % (related_url, name)
		output += '<img src="%simg/admin/selector-search.gif" width="16" height="16" alt="%s" />' % (settings.ADMIN_MEDIA_PREFIX, _('Lookup'))
		output += '</a>'
		if value:
			value_class = self.content_type.model_class()
			try:
				value_object = value_class.objects.get(pk=value)
				output += '&nbsp;<strong>%s</strong>' % escape(truncate_words(value_object, 14))
			except value_class.DoesNotExist:
				pass
		return mark_safe(output)