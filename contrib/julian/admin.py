from django.contrib import admin
from philo.admin import EntityAdmin, COLLAPSE_CLASSES
from philo.contrib.julian.models import Location, Event, Calendar, ICalendarFeedView


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
			'fields': ('parent_event', 'uuid',),
			'classes': COLLAPSE_CLASSES
		})
	)
	related_lookup_fields = {
		'generic': [["location_content_type", "location_pk"]]
	}
	filter_horizontal = ['tags']
	raw_id_fields = ['parent_event']


class CalendarAdmin(EntityAdmin):
	pass


class ICalendarFeedViewAdmin(EntityAdmin):
	pass


admin.site.register(Location, LocationAdmin)
admin.site.register(Event, EventAdmin)
admin.site.register(Calendar, CalendarAdmin)
admin.site.register(ICalendarFeedView, ICalendarFeedViewAdmin)