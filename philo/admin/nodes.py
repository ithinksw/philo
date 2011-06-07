from django.contrib import admin
from mptt.admin import MPTTModelAdmin

from philo.admin.base import EntityAdmin, TreeEntityAdmin, COLLAPSE_CLASSES
from philo.models import Node, Redirect, File


class NodeAdmin(TreeEntityAdmin):
	list_display = ('slug', 'view', 'accepts_subpath')
	raw_id_fields = ('parent',)
	related_lookup_fields = {
		'fk': raw_id_fields,
		'm2m': [],
		'generic': [['view_content_type', 'view_object_id']]
	}
	
	def accepts_subpath(self, obj):
		return obj.accepts_subpath
	accepts_subpath.boolean = True
	
	def formfield_for_foreignkey(self, db_field, request, **kwargs):
		return super(MPTTModelAdmin, self).formfield_for_foreignkey(db_field, request, **kwargs)


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
	related_lookup_fields = {
		'fk': raw_id_fields
	}


class FileAdmin(ViewAdmin):
	fieldsets = (
		(None, {
			'fields': ('name', 'file', 'mimetype')
		}),
	)
	list_display = ('name', 'mimetype', 'file')
	search_fields = ('name',)
	list_filter = ('mimetype',)


admin.site.register(Node, NodeAdmin)
admin.site.register(Redirect, RedirectAdmin)
admin.site.register(File, FileAdmin)