from django.db import models
from philo.models.base import Tag, Entity, Titled
import datetime

class Location(Entity, Titled):
	slug = models.SlugField(max_length=255, unique=True)


class Calendar(Entity, Titled):
	slug = models.SlugField(max_length=255, unique=True)


class Event(Entity, Titled):
	description = models.TextField()
	start_time = models.DateTimeField()
	end_time = models.DateTimeField()
	is_all_day_event = models.BooleanField(default=False)
	time_created = models.DateTimeField(default=datetime.datetime.now)
	location = models.ForeignKey(Location)
	calendars = models.ManyToManyField(Calendar)
	tags = models.ManyToManyField(Tag)

