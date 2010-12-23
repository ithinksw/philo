from django.contrib import admin
from philo.admin.base import EntityAdmin, TreeEntityAdmin
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