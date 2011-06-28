from django.contrib import admin

from philo.admin import TreeEntityAdmin, COLLAPSE_CLASSES, NodeAdmin, EntityAdmin
from philo.models import Node
from philo.contrib.shipherd.models import NavigationItem, Navigation


NAVIGATION_RAW_ID_FIELDS = ('navigation', 'parent', 'target_node')


class NavigationItemInline(admin.StackedInline):
	raw_id_fields = NAVIGATION_RAW_ID_FIELDS
	model = NavigationItem
	extra = 0
	sortable_field_name = 'order'
	ordering = ('order',)
	related_lookup_fields = {'fk': raw_id_fields}


class NavigationItemChildInline(NavigationItemInline):
	verbose_name = "child"
	verbose_name_plural = "children"
	fieldsets = (
		(None, {
			'fields': ('text', 'parent')
		}),
		('Target', {
			'fields': ('target_node', 'url_or_subpath',)
		}),
		('Advanced', {
			'fields': ('reversing_parameters', 'order'),
			'classes': COLLAPSE_CLASSES
		})
	)


class NavigationNavigationItemInline(NavigationItemInline):
	fieldsets = (
		(None, {
			'fields': ('text', 'navigation')
		}),
		('Target', {
			'fields': ('target_node', 'url_or_subpath',)
		}),
		('Advanced', {
			'fields': ('reversing_parameters', 'order'),
			'classes': COLLAPSE_CLASSES
		})
	)


class NodeNavigationItemInline(NavigationItemInline):
	verbose_name_plural = 'targeting navigation'
	fieldsets = (
		(None, {
			'fields': ('text',)
		}),
		('Target', {
			'fields': ('target_node', 'url_or_subpath',)
		}),
		('Advanced', {
			'fields': ('reversing_parameters', 'order'),
			'classes': COLLAPSE_CLASSES
		}),
		('Expert', {
			'fields': ('parent', 'navigation')
		}),
	)


class NodeNavigationInline(admin.TabularInline):
	model = Navigation
	extra = 0


NodeAdmin.inlines = [NodeNavigationInline, NodeNavigationItemInline] + NodeAdmin.inlines


class NavigationItemAdmin(TreeEntityAdmin):
	list_display = ('__unicode__', 'target_node', 'url_or_subpath', 'reversing_parameters')
	fieldsets = (
		(None, {
			'fields': ('text', 'navigation',)
		}),
		('Target', {
			'fields': ('target_node', 'url_or_subpath',)
		}),
		('Advanced', {
			'fields': ('reversing_parameters',),
			'classes': COLLAPSE_CLASSES
		}),
		('Expert', {
			'fields': ('parent', 'order'),
			'classes': COLLAPSE_CLASSES
		})
	)
	raw_id_fields = NAVIGATION_RAW_ID_FIELDS
	related_lookup_fields = {'fk': raw_id_fields}
	inlines = [NavigationItemChildInline] + TreeEntityAdmin.inlines


class NavigationAdmin(EntityAdmin):
	inlines = [NavigationNavigationItemInline]
	raw_id_fields = ['node']
	related_lookup_fields = {'fk': raw_id_fields}


admin.site.unregister(Node)
admin.site.register(Node, NodeAdmin)
admin.site.register(Navigation, NavigationAdmin)
admin.site.register(NavigationItem, NavigationItemAdmin)