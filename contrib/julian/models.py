from django.db import models
from philo.models.base import Tag, Entity, Titled
import datetime

if not hasattr(settings, 'PHILO_LOCATION_MODULE'):
	class Location(Entity, Titled):
		slug = models.SlugField(max_length=255, unique=True)


if not hasattr(settings, 'PHILO_CALENDAR_MODULE'):
	class Calendar(Entity, Titled):
		slug = models.SlugField(max_length=255, unique=True)


class Event(Entity, Titled):
	description = models.TextField()
	start_time = models.DateTimeField()
	end_time = models.DateTimeField()
	is_all_day_event = models.BooleanField(default=False)
	time_created = models.DateTimeField(default=datetime.datetime.now)
	location = models.ForeignKey(getattr(settings, 'PHILO_LOCATION_MODULE', Location), related_name='events')
	calendars = models.ManyToManyField(getattr(settings, 'PHILO_CALENDAR_MODULE', Calendar), related_name='events')
	tags = models.ManyToManyField(Tag)

