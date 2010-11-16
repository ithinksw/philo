from django.contrib import admin
from philo.admin.base import EntityAdmin, TreeEntityAdmin, COLLAPSE_CLASSES
from philo.models import Node, Redirect, File, NodeNavigationOverride
from philo.forms import NodeWithOverrideForm


class ChildNavigationOverrideInline(admin.StackedInline):
	fk_name = 'parent'
	model = NodeNavigationOverride
	sortable_field_name = 'order'
	verbose_name = 'child'
	verbose_name_plural = 'children'
	extra = 0
	max_num = 0


class NodeAdmin(TreeEntityAdmin):
	form = NodeWithOverrideForm
	fieldsets = (
		(None, {
			'fields': ('parent', 'slug', 'view_content_type', 'view_object_id'),
		}),
		('Navigation Overrides', {
			'fields': ('title', 'url', 'child_navigation'),
			'classes': COLLAPSE_CLASSES
		})
	)
	inlines = [ChildNavigationOverrideInline] + TreeEntityAdmin.inlines


class ViewAdmin(EntityAdmin):
	pass


class RedirectAdmin(ViewAdmin):
	fieldsets = (
		(None, {
			'fields': ('target', 'status_code')
		}),
	)
	list_display = ('target', 'status_code')
	list_filter = ('status_code',)


class FileAdmin(ViewAdmin):
	fieldsets = (
		(None, {
			'fields': ('file', 'mimetype')
		}),
	)
	list_display = ('mimetype', 'file')


admin.site.register(Node, NodeAdmin)
admin.site.register(Redirect, RedirectAdmin)
admin.site.register(File, FileAdmin)