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
			containers = template.containers
			if len(containers) > 0:
				for container in containers:
					fieldsets.append((('Container: %s' % container), {
						'fields': (('container_content_%s' % container), ('container_dynamic_%s' % container))
					}))
		return fieldsets
	
	def get_form(self, request, obj=None, **kwargs):
		form = super(PageAdmin, self).get_form(request, obj, **kwargs)
		if obj: # if no obj, creating a new page, thus no template set, thus no containers
			page = obj
			template = page.template
			containers = template.containers
			for container in containers:
				initial_content = None
				initial_dynamic = False
				try:
					contentlet = page.contentlets.get(name__exact=container)
					initial_content = contentlet.content
					initial_dynamic = contentlet.dynamic
				except Contentlet.DoesNotExist:
					pass
				form.base_fields[('container_content_%s' % container)] = forms.CharField(label='Content', widget=forms.Textarea(), initial=initial_content, required=False)
				form.base_fields[('container_dynamic_%s' % container)] = forms.BooleanField(label='Dynamic', help_text='Specify whether this content contains dynamic template code', initial=initial_dynamic, required=False)
		return form
	
	def save_model(self, request, page, form, change):
		page.save()
		
		template = page.template
		containers = template.containers
		for container in containers:
			if (("container_content_%s" % container) in form.cleaned_data) and (("container_dynamic_%s" % container) in form.cleaned_data):
				content = form.cleaned_data[('container_content_%s' % container)]
				dynamic = form.cleaned_data[('container_dynamic_%s' % container)]
				contentlet, created = page.contentlets.get_or_create(name=container, defaults={'content': content, 'dynamic': dynamic})
				if not created:
					contentlet.content = content
					contentlet.dynamic = dynamic
					contentlet.save()


admin.site.register(Collection, CollectionAdmin)
admin.site.register(Page, PageAdmin)
admin.site.register(Template, TemplateAdmin)
