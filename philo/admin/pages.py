from django import forms
from django.conf import settings
from django.contrib import admin

from philo.admin.base import COLLAPSE_CLASSES, TreeEntityAdmin
from philo.admin.forms.containers import *
from philo.admin.nodes import ViewAdmin
from philo.admin.widgets import EmbedWidget
from philo.models.fields import TemplateField
from philo.models.pages import Page, Template, Contentlet, ContentReference


class ContainerInline(admin.StackedInline):
	extra = 0
	max_num = 0
	can_delete = False
	classes = ('collapse-open', 'collapse','open')
	if 'grappelli' in settings.INSTALLED_APPS:
		template = 'admin/philo/edit_inline/grappelli_tabular_container.html'
	else:
		template = 'admin/philo/edit_inline/tabular_container.html'


class ContentletInline(ContainerInline):
	model = Contentlet
	formset = ContentletInlineFormSet
	form = ContentletForm


class ContentReferenceInline(ContainerInline):
	model = ContentReference
	formset = ContentReferenceInlineFormSet
	form = ContentReferenceForm


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
	inlines = [ContentletInline, ContentReferenceInline] + ViewAdmin.inlines
	
	def response_add(self, request, obj, post_url_continue='../%s/'):
		# Shamelessly cribbed from django/contrib/auth/admin.py:143
		if '_addanother' not in request.POST and '_popup' not in request.POST:
			request.POST['_continue'] = 1
		return super(PageAdmin, self).response_add(request, obj, post_url_continue)


class TemplateAdmin(TreeEntityAdmin):
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
	formfield_overrides = {
		TemplateField: {'widget': EmbedWidget}
	}
	save_on_top = True
	save_as = True
	list_display = ('__unicode__', 'slug', 'get_path',)


admin.site.register(Page, PageAdmin)
admin.site.register(Template, TemplateAdmin)