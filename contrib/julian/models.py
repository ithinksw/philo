from django.db import models
from django.contrib.auth.models import User
from philo.models.base import Tag, Entity, Titled
import datetime

if not hasattr(settings, 'PHILO_LOCATION_MODULE'):
	class Location(Entity, Titled):
		slug = models.SlugField(max_length=255, unique=True)

# Needs to be organised in a sensical order.
class Event(Entity, Titled):
	description = models.TextField()
	start_time = models.DateTimeField(blank=True, null=True)
	end_time = models.DateTimeField(blank=True, null=True)
	is_all_day_event = models.BooleanField(default=False)
	location = models.ForeignKey(getattr(settings, 'PHILO_LOCATION_MODULE', Location), related_name='events', blank=True, null=True)
	tags = models.ManyToManyField(Tag, blank=True, null=True)
	parent_event = models.ForeignKey(Event, blank=True, null=True)				# To handle series' of events.
	user = models.ForeignKey(getattr(settings, 'PHILO_PERSON_MODULE', User)) 	# Should this be optional?
	url = models.URLField(blank=True, null=True)
	attachment = models.FileField(upload_to='events/attachments/%Y/%m/%d', blank=True, null=True)
	image = models.ImageField(upload_to='events/images/%Y/%m/%d', blank=True, null=True)


class Calendar(Entity, Titled):
	slug = models.SlugField(max_length=255, unique=True)
	events = models.ManyToManyField(Event, related_name='calendars')
	
# NOTES: Only let start time be blank if it has child events with times.