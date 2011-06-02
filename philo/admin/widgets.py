from django import forms
from django.conf import settings
from django.contrib.admin.widgets import FilteredSelectMultiple, url_params_from_lookup_dict
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


class TagFilteredSelectMultiple(FilteredSelectMultiple):
	"""
	A SelectMultiple with a JavaScript filter interface.

	Note that the resulting JavaScript assumes that the jsi18n
	catalog has been loaded in the page
	"""
	class Media:
		js = (
			settings.ADMIN_MEDIA_PREFIX + "js/core.js",
			settings.ADMIN_MEDIA_PREFIX + "js/SelectBox.js",
			settings.ADMIN_MEDIA_PREFIX + "js/SelectFilter2.js",
			"philo/js/TagCreation.js",
		)

	def render(self, name, value, attrs=None, choices=()):
		if attrs is None: attrs = {}
		attrs['class'] = 'selectfilter'
		if self.is_stacked: attrs['class'] += 'stacked'
		output = [super(FilteredSelectMultiple, self).render(name, value, attrs, choices)]
		output.append(u'<script type="text/javascript">addEvent(window, "load", function(e) {')
		# TODO: "id_" is hard-coded here. This should instead use the correct
		# API to determine the ID dynamically.
		output.append(u'SelectFilter.init("id_%s", "%s", %s, "%s"); tagCreation.init("id_%s"); });</script>\n' % \
			(name, self.verbose_name.replace('"', '\\"'), int(self.is_stacked), settings.ADMIN_MEDIA_PREFIX, name))
		return mark_safe(u''.join(output))