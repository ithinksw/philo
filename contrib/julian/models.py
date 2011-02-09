from django.conf import settings
from django.contrib.localflavor.us.models import USStateField
from django.contrib.contenttypes.generic import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator, MinValueValidator, MaxValueValidator
from django.db import models
from philo.contrib.julian.fields import USZipCodeField
from philo.models.base import Tag, Entity, Titled
from philo.models.fields import TemplateField
from philo.utils import ContentTypeSubclassLimiter
import datetime
import re


# TODO: Could this regex more closely match the Formal Public Identifier spec?
# http://xml.coverpages.org/tauber-fpi.html
FPI_REGEX = re.compile(r"(|\+//|-//)[^/]+//[^/]+//[A-Z]{2}")


class Location(Entity):
	name = models.CharField(max_length=150, blank=True)
	description = models.TextField(blank=True)
	
	longitude = models.FloatField(blank=True, validators=[MinValueValidator(-180), MaxValueValidator(180)])
	latitude = models.FloatField(blank=True, validators=[MinValueValidator(-90), MaxValueValidator(90)])
	
	events = GenericRelation('Event')
	
	def clean(self):
		if not (self.name or self.description) or (self.longitude is None and self.latitude is None):
			raise ValidationError("Either a name and description or a latitude and longitude must be defined.")
	
	class Meta:
		abstract = True


_location_content_type_limiter = ContentTypeSubclassLimiter(Location)


# TODO: Can we track when a building is open? Hmm...
class Building(Location):
	"""A building is a location with a street address."""
	address = models.CharField(max_length=255)
	city = models.CharField(max_length=150)
	
	class Meta:
		abstract = True


_building_content_type_limiter = ContentTypeSubclassLimiter(Building)


class USBuilding(Building):
	state = USStateField()
	zipcode = USZipCodeField()
	
	class Meta:
		verbose_name = "Building (US)"
		verbose_name_plural = "Buildings (US)"


class Venue(Location):
	"""A venue is a location inside a building"""
	building_content_type = models.ForeignKey(ContentType, limit_choices_to=_building_content_type_limiter)
	building_pk = models.TextField()
	building = GenericForeignKey('building_content_type', 'building_pk')


class TimedModel(models.Model):
	start_date = models.DateField(help_text="YYYY-MM-DD")
	start_time = models.TimeField(blank=True, null=True, help_text="HH:MM:SS - 24 hour clock")
	end_date = models.DateField()
	end_time = models.TimeField(blank=True, null=True)
	
	def is_all_day(self):
		return self.start_time is None and self.end_time is None
	
	class Meta:
		abstract = True


class Event(Entity, Titled, TimedModel):
	location_content_type = models.ForeignKey(ContentType, limit_choices_to=_location_content_type_limiter)
	location_pk = models.TextField()
	location = GenericForeignKey('location_content_type', 'location_pk')
	
	description = TemplateField()
	
	tags = models.ManyToManyField(Tag, blank=True, null=True)
	
	parent_event = models.ForeignKey('self', blank=True, null=True)
	
	owner = models.ForeignKey(getattr(settings, 'PHILO_PERSON_MODULE', 'auth.User'))


class Calendar(Entity):
	name = models.CharField(max_length=100)
	#slug = models.SlugField(max_length=255, unique=True)
	events = models.ManyToManyField(Event, related_name='calendars')
	
	# TODO: Can we auto-generate this on save based on site id and calendar name and settings language?
	uuid = models.CharField("Calendar UUID", max_length=100, unique=True, help_text="Should conform to Formal Public Identifier format. See <http://en.wikipedia.org/wiki/Formal_Public_Identifier>", validators=[RegexValidator(FPI_REGEX)])