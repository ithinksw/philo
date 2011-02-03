from django.contrib import admin
from philo.admin.base import EntityAdmin, TreeEntityAdmin, COLLAPSE_CLASSES
from philo.models import Node, Redirect, File


class NodeAdmin(TreeEntityAdmin):
	list_display = ('slug', 'view', 'accepts_subpath')
	
	def accepts_subpath(self, obj):
		return obj.accepts_subpath
	accepts_subpath.boolean = True


class ViewAdmin(EntityAdmin):
	pass


class RedirectAdmin(ViewAdmin):
	fieldsets = (
		(None, {
			'fields': ('target_node', 'url_or_subpath', 'status_code')
		}),
		('Advanced', {
			'fields': ('reversing_parameters',),
			'classes': COLLAPSE_CLASSES
		})
	)
	list_display = ('target_url', 'status_code', 'target_node', 'url_or_subpath')
	list_filter = ('status_code',)
	raw_id_fields = ['target_node']
	related_field_lookups = {
		'fk': ['target_node']
	}


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