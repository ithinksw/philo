from django.conf import settings
from django.contrib.contenttypes.generic import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from philo.models.base import Tag, Entity
from philo.models.fields import TemplateField
from philo.utils import ContentTypeRegistryLimiter
import re


# TODO: Could this regex more closely match the Formal Public Identifier spec?
# http://xml.coverpages.org/tauber-fpi.html
FPI_REGEX = re.compile(r"(|\+//|-//)[^/]+//[^/]+//[A-Z]{2}")


location_content_type_limiter = ContentTypeRegistryLimiter()


def register_location_model(model):
	location_content_type_limiter.register_class(model)


def unregister_location_model(model):
	location_content_type_limiter.unregister_class(model)


class Location(Entity):
	name = models.CharField(max_length=255)
	
	def __unicode__(self):
		return self.name


register_location_model(Location)


class TimedModel(models.Model):
	start_date = models.DateField(help_text="YYYY-MM-DD")
	start_time = models.TimeField(blank=True, null=True, help_text="HH:MM:SS - 24 hour clock")
	end_date = models.DateField()
	end_time = models.TimeField(blank=True, null=True)
	
	def is_all_day(self):
		return self.start_time is None and self.end_time is None
	
	def clean(self):
		if bool(self.start_time) != bool(self.end_time):
			raise ValidationError("A %s must have either a start time and an end time or neither.")
		
		if self.start_date > self.end_date or self.start_date == self.end_date and self.start_time > self.end_time:
			raise ValidationError("A %s cannot end before it starts." % self.__class__.__name__)
	
	class Meta:
		abstract = True


class Event(Entity, TimedModel):
	name = models.CharField(max_length=255)
	slug = models.SlugField(max_length=255)
	
	location_content_type = models.ForeignKey(ContentType, limit_choices_to=location_content_type_limiter)
	location_pk = models.TextField()
	location = GenericForeignKey('location_content_type', 'location_pk')
	
	description = TemplateField()
	
	tags = models.ManyToManyField(Tag, blank=True, null=True)
	
	parent_event = models.ForeignKey('self', blank=True, null=True)
	
	owner = models.ForeignKey(getattr(settings, 'PHILO_PERSON_MODULE', 'auth.User'))
	
	# TODO: Add uid - use as pk?


class Calendar(Entity):
	name = models.CharField(max_length=100)
	#slug = models.SlugField(max_length=255, unique=True)
	events = models.ManyToManyField(Event, related_name='calendars')
	
	# TODO: Can we auto-generate this on save based on site id and calendar name and settings language?
	uuid = models.CharField("Calendar UUID", max_length=100, unique=True, help_text="Should conform to Formal Public Identifier format. See <http://en.wikipedia.org/wiki/Formal_Public_Identifier>", validators=[RegexValidator(FPI_REGEX)])