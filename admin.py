from django.contrib import admin
from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType
from django import forms
from models import *


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
					initial_content = page.contentreferences.get(name__exact=container_name, content_type=container_content_type)
				except ContentReference.DoesNotExist:
					pass
				form.base_fields[('contentreference_container_%s' % container_name)] = forms.ModelChoiceField(label='References', initial=initial_content, required=False, queryset=container_content_type.model_class().objects.all())
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
