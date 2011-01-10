from django.contrib import admin
from philo.admin import TreeEntityAdmin, COLLAPSE_CLASSES, NodeAdmin
from philo.contrib.shipherd.models import Navigation


NAVIGATION_RAW_ID_FIELDS = ('hosting_node', 'parent', 'target_node')


class NavigationInline(admin.StackedInline):
	fieldsets = (
		(None, {
			'fields': ('text',)
		}),
		('Target', {
			'fields': ('target_node', 'url_or_subpath',)
		}),
		('Advanced', {
			'fields': ('reversing_parameters', 'order', 'depth'),
			'classes': COLLAPSE_CLASSES
		}),
		('Expert', {
			'fields': ('hosting_node', 'parent'),
			'classes': COLLAPSE_CLASSES
		})
	)
	raw_id_fields = NAVIGATION_RAW_ID_FIELDS
	model = Navigation
	extra = 1
	sortable_field_name = 'order'


class NavigationNavigationInline(NavigationInline):
	verbose_name = "child"
	verbose_name_plural = "children"


class NodeNavigationInline(NavigationInline):
	verbose_name_plural = 'navigation'


class NavigationAdmin(TreeEntityAdmin):
	list_display = ('__unicode__', 'target_node', 'url_or_subpath', 'reversing_parameters')
	fieldsets = (
		(None, {
			'fields': ('text', 'hosting_node',)
		}),
		('Target', {
			'fields': ('target_node', 'url_or_subpath',)
		}),
		('Advanced', {
			'fields': ('reversing_parameters', 'depth'),
			'classes': COLLAPSE_CLASSES
		}),
		('Expert', {
			'fields': ('parent', 'order'),
			'classes': COLLAPSE_CLASSES
		})
	)
	raw_id_fields = NAVIGATION_RAW_ID_FIELDS
	inlines = [NavigationNavigationInline] + TreeEntityAdmin.inlines


NodeAdmin.inlines = [NodeNavigationInline] + NodeAdmin.inlines


admin.site.register(Navigation, NavigationAdmin)