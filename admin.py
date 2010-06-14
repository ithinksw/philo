from django.contrib import admin
from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType
from django import forms
from django.conf import settings
from django.utils.translation import ugettext as _
from django.utils.safestring import mark_safe
from django.utils.html import escape
from django.utils.text import truncate_words
from philo.models import *


class AttributeInline(generic.GenericTabularInline):
	ct_field = 'entity_content_type'
	ct_fk_field = 'entity_object_id'
	model = Attribute
	extra = 1
	classes = ('collapse-closed',)
	allow_add = True


class RelationshipInline(generic.GenericTabularInline):
	ct_field = 'entity_content_type'
	ct_fk_field = 'entity_object_id'
	model = Relationship
	extra = 1
	classes = ('collapse-closed',)
	allow_add = True


class EntityAdmin(admin.ModelAdmin):
	inlines = [AttributeInline, RelationshipInline]
	save_on_top = True


class CollectionMemberInline(admin.TabularInline):
	fk_name = 'collection'
	model = CollectionMember
	extra = 1
	classes = ('collapse-closed',)
	allow_add = True


class CollectionAdmin(admin.ModelAdmin):
	inlines = [CollectionMemberInline]


class TemplateAdmin(admin.ModelAdmin):
	prepopulated_fields = {'slug': ('name',)}
	fieldsets = (
		(None, {
			'fields': ('parent', 'name', 'slug')
		}),
		('Documentation', {
			'classes': ('collapse', 'collapse-closed'),
			'fields': ('documentation',)
		}),
		(None, {
			'fields': ('code',)
		}),
		('Advanced', {
			'classes': ('collapse','collapse-closed'),
			'fields': ('mimetype',)
		}),
	)
	save_on_top = True
	save_as = True


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


class PageAdmin(EntityAdmin):
	prepopulated_fields = {'slug': ('title',)}
	fieldsets = (
		(None, {
			'fields': ('title', 'template')
		}),
		('URL/Tree/Hierarchy', {
			'classes': ('collapse', 'collapse-closed'),
			'fields': ('parent', 'slug')
		}),
	)
	list_display = ('title', 'path', 'template')
	list_filter = ('template',)
	search_fields = ['title', 'slug', 'contentlets__content']
	
	def get_fieldsets(self, request, obj=None, **kwargs):
		fieldsets = list(self.fieldsets)
		if obj: # if no obj, creating a new page, thus no template set, thus no containers
			page = obj
			template = page.template
			contentlet_containers, contentreference_containers = template.containers
			for container_name in contentlet_containers:
				fieldsets.append((('Container: %s' % container_name), {
					'fields': (('contentlet_container_content_%s' % container_name), ('contentlet_container_dynamic_%s' % container_name))
				}))
			for container_name, container_content_type in contentreference_containers:
				fieldsets.append((('Container: %s' % container_name), {
					'fields': (('contentreference_container_%s' % container_name),)
				}))
		return fieldsets
	
	def get_form(self, request, obj=None, **kwargs):
		form = super(PageAdmin, self).get_form(request, obj, **kwargs)
		if obj: # if no obj, creating a new page, thus no template set, thus no containers
			page = obj
			template = page.template
			contentlet_containers, contentreference_containers = template.containers
			for container_name in contentlet_containers:
				initial_content = None
				initial_dynamic = False
				try:
					contentlet = page.contentlets.get(name__exact=container_name)
					initial_content = contentlet.content
					initial_dynamic = contentlet.dynamic
				except Contentlet.DoesNotExist:
					pass
				form.base_fields[('contentlet_container_content_%s' % container_name)] = forms.CharField(label='Content', widget=forms.Textarea(), initial=initial_content, required=False)
				form.base_fields[('contentlet_container_dynamic_%s' % container_name)] = forms.BooleanField(label='Dynamic', help_text='Specify whether this content contains dynamic template code', initial=initial_dynamic, required=False)
			for container_name, container_content_type in contentreference_containers:
				initial_content = None
				try:
					initial_content = page.contentreferences.get(name__exact=container_name, content_type=container_content_type).content.pk
				except ContentReference.DoesNotExist:
					pass
				form.base_fields[('contentreference_container_%s' % container_name)] = forms.ModelChoiceField(label='References', widget=ModelLookupWidget(container_content_type), initial=initial_content, required=False, queryset=container_content_type.model_class().objects.all())
		return form
	
	def save_model(self, request, page, form, change):
		page.save()
		template = page.template
		contentlet_containers, contentreference_containers = template.containers
		for container_name in contentlet_containers:
			if (('contentlet_container_content_%s' % container_name) in form.cleaned_data) and (('contentlet_container_dynamic_%s' % container_name) in form.cleaned_data):
				content = form.cleaned_data[('contentlet_container_content_%s' % container_name)]
				dynamic = form.cleaned_data[('contentlet_container_dynamic_%s' % container_name)]
				contentlet, created = page.contentlets.get_or_create(name=container_name, defaults={'content': content, 'dynamic': dynamic})
				if not created:
					contentlet.content = content
					contentlet.dynamic = dynamic
					contentlet.save()
		for container_name, container_content_type in contentreference_containers:
			if ('contentreference_container_%s' % container_name) in form.cleaned_data:
				content = form.cleaned_data[('contentreference_container_%s' % container_name)]
				contentreference, created = page.contentreferences.get_or_create(name=container_name, defaults={'content': content})
				if not created:
					contentreference.content = content
					contentreference.save()


admin.site.register(Collection, CollectionAdmin)
admin.site.register(Redirect)
admin.site.register(File)
admin.site.register(Page, PageAdmin)
admin.site.register(Template, TemplateAdmin)
