from django.contrib import admin
from django import forms
from philo.admin import widgets
from philo.admin.base import COLLAPSE_CLASSES
from philo.admin.nodes import ViewAdmin
from philo.models.pages import Page, Template, Contentlet, ContentReference


class PageAdmin(ViewAdmin):
	add_form_template = 'admin/philo/page/add_form.html'
	fieldsets = (
		(None, {
			'fields': ('title', 'template')
		}),
	)
	list_display = ('title', 'template')
	list_filter = ('template',)
	search_fields = ['title', 'contentlets__content']
	
	def get_fieldsets(self, request, obj=None, **kwargs):
		fieldsets = list(self.fieldsets)
		if obj: # if no obj, creating a new page, thus no template set, thus no containers
			template = obj.template
			if template.documentation:
				fieldsets.append(('Template Documentation', {
					'description': template.documentation
				}))
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
				except (ContentReference.DoesNotExist, AttributeError):
					pass
				form.base_fields[('contentreference_container_%s' % container_name)] = forms.ModelChoiceField(label='References', widget=widgets.ModelLookupWidget(container_content_type), initial=initial_content, required=False, queryset=container_content_type.model_class().objects.all())
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
				try:
					contentreference = page.contentreferences.get(name=container_name)
				except ContentReference.DoesNotExist:
					contentreference = ContentReference(name=container_name, page=page, content_type=container_content_type)
				else:
					if content == None:
						contentreference.delete()
				
				if content is not None:
					contentreference.content_id = content.id
					contentreference.save()


class TemplateAdmin(admin.ModelAdmin):
	prepopulated_fields = {'slug': ('name',)}
	fieldsets = (
		(None, {
			'fields': ('parent', 'name', 'slug')
		}),
		('Documentation', {
			'classes': COLLAPSE_CLASSES,
			'fields': ('documentation',)
		}),
		(None, {
			'fields': ('code',)
		}),
		('Advanced', {
			'classes': COLLAPSE_CLASSES,
			'fields': ('mimetype',)
		}),
	)
	save_on_top = True
	save_as = True
	list_display = ('__unicode__', 'slug', 'get_path',)


admin.site.register(Page, PageAdmin)
admin.site.register(Template, TemplateAdmin)