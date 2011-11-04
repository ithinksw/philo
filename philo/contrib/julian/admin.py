from django.contrib import admin

from philo.admin import EntityAdmin, COLLAPSE_CLASSES
from philo.contrib.julian.models import Location, Event, Calendar, CalendarView


class LocationAdmin(EntityAdmin):
	pass


class EventAdmin(EntityAdmin):
	fieldsets = (
		(None, {
			'fields': ('name', 'slug', 'description', 'tags', 'owner')
		}),
		('Location', {
			'fields': ('location_content_type', 'location_pk')
		}),
		('Time', {
			'fields': (('start_date', 'start_time'), ('end_date', 'end_time'),),
		}),
		('Advanced', {
			'fields': ('parent_event', 'site',),
			'classes': COLLAPSE_CLASSES
		})
	)
	filter_horizontal = ['tags']
	raw_id_fields = ['parent_event']
	related_lookup_fields = {
		'fk': raw_id_fields,
		'generic': [["location_content_type", "location_pk"]]
	}
	prepopulated_fields = {'slug': ('name',)}


class CalendarAdmin(EntityAdmin):
	prepopulated_fields = {'slug': ('name',)}
	filter_horizontal = ['events']
	fieldsets = (
		(None, {
			'fields': ('name', 'description', 'events')
		}),
		('Advanced', {
			'fields': ('slug', 'site', 'language',),
			'classes': COLLAPSE_CLASSES
		})
	)


class CalendarViewAdmin(EntityAdmin):
	fieldsets = (
		(None, {
			'fields': ('calendar',)
		}),
		('Pages', {
			'fields': ('index_page', 'event_detail_page')
		}),
		('General Settings', {
			'fields': ('tag_permalink_base', 'owner_permalink_base', 'location_permalink_base', 'events_per_page')
		}),
		('Event List Pages', {
			'fields': ('timespan_page', 'tag_page', 'location_page', 'owner_page'),
			'classes': COLLAPSE_CLASSES
		}),
		('Archive Pages', {
			'fields': ('location_archive_page', 'tag_archive_page', 'owner_archive_page'),
			'classes': COLLAPSE_CLASSES
		}),
		('Feed Settings', {
			'fields': ( 'feeds_enabled', 'feed_suffix', 'feed_type', 'item_title_template', 'item_description_template',),
			'classes': COLLAPSE_CLASSES
		})
	)
	raw_id_fields = ('index_page', 'event_detail_page', 'timespan_page', 'tag_page', 'location_page', 'owner_page', 'location_archive_page', 'tag_archive_page', 'owner_archive_page', 'item_title_template', 'item_description_template',)
	related_lookup_fields = {'fk': raw_id_fields}


admin.site.register(Location, LocationAdmin)
admin.site.register(Event, EventAdmin)
admin.site.register(Calendar, CalendarAdmin)
admin.site.register(CalendarView, CalendarViewAdmin)