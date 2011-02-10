from django.conf import settings
from django.conf.urls.defaults import url, patterns, include
from django.contrib.auth.models import User
from django.contrib.contenttypes.generic import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from django.http import HttpResponse
from django.utils.encoding import force_unicode
from philo.contrib.julian.feedgenerator import ICalendarFeed
from philo.contrib.penfield.models import FeedView, FEEDS
from philo.models.base import Tag, Entity
from philo.models.fields import TemplateField
from philo.utils import ContentTypeRegistryLimiter
import re


# TODO: Could this regex more closely match the Formal Public Identifier spec?
# http://xml.coverpages.org/tauber-fpi.html
FPI_REGEX = re.compile(r"(|\+//|-//)[^/]+//[^/]+//[A-Z]{2}")


ICALENDAR = ICalendarFeed.mime_type
FEEDS[ICALENDAR] = ICalendarFeed


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
	
	def get_start(self):
		return self.start_date
	
	def get_end(self):
		return self.end_date
	
	class Meta:
		abstract = True


class Event(Entity, TimedModel):
	name = models.CharField(max_length=255)
	slug = models.SlugField(max_length=255)
	
	location_content_type = models.ForeignKey(ContentType, limit_choices_to=location_content_type_limiter, blank=True, null=True)
	location_pk = models.TextField(blank=True)
	location = GenericForeignKey('location_content_type', 'location_pk')
	
	description = TemplateField()
	
	tags = models.ManyToManyField(Tag, blank=True, null=True)
	
	parent_event = models.ForeignKey('self', blank=True, null=True)
	
	owner = models.ForeignKey(getattr(settings, 'PHILO_PERSON_MODULE', 'auth.User'))
	
	created = models.DateTimeField(auto_now_add=True)
	last_modified = models.DateTimeField(auto_now=True)
	uuid = models.TextField() # Format?


class Calendar(Entity):
	name = models.CharField(max_length=100)
	slug = models.SlugField(max_length=100)
	description = models.TextField(blank=True)
	#slug = models.SlugField(max_length=255, unique=True)
	events = models.ManyToManyField(Event, related_name='calendars')
	
	# TODO: Can we auto-generate this on save based on site id and calendar name and settings language?
	uuid = models.TextField("Calendar UUID", unique=True, help_text="Should conform to Formal Public Identifier format. See &lt;http://en.wikipedia.org/wiki/Formal_Public_Identifier&gt;", validators=[RegexValidator(FPI_REGEX)])


class ICalendarFeedView(FeedView):
	calendar = models.ForeignKey(Calendar)
	
	item_context_var = "events"
	object_attr = "calendar"
	
	def get_reverse_params(self, obj):
		return 'feed', [], {}
	
	@property
	def urlpatterns(self):
		return patterns('',
			url(r'^$', self.feed_view('get_all_events', 'feed'), name='feed')
		)
	
	def feed_view(self, get_items_attr, reverse_name):
		"""
		Returns a view function that renders a list of items as a feed.
		"""
		get_items = callable(get_items_attr) and get_items_attr or getattr(self, get_items_attr)
		
		def inner(request, extra_context=None, *args, **kwargs):
			obj = self.get_object(request, *args, **kwargs)
			feed = self.get_feed(obj, request, reverse_name)
			items, xxx = get_items(request, extra_context=extra_context, *args, **kwargs)
			self.populate_feed(feed, items, request)
			
			response = HttpResponse(mimetype=feed.mime_type)
			feed.write(response, 'utf-8')
			
			if FEEDS[self.feed_type] == ICalendarFeed:
				# Add some extra information to the response for iCalendar readers.
				# <http://blog.thescoop.org/archives/2007/07/31/django-ical-and-vobject/>
				# Also, __get_dynamic_attr is protected by python - mangled. Should it
				# just be private?
				filename = self._FeedView__get_dynamic_attr('filename', obj)
				response['Filename'] = filename
				response['Content-Disposition'] = 'attachment; filename=%s' % filename
			return response
		
		return inner
	
	def get_event_queryset(self):
		return self.calendar.events.all()
	
	def get_all_events(self, request, extra_context=None):
		return self.get_event_queryset(), extra_context
	
	def title(self, obj):
		return obj.name
	
	def link(self, obj):
		# Link is ignored anyway...
		return ""
	
	def filename(self, obj):
		return "%s.ics" % obj.slug
	
	def feed_guid(self, obj):
		# Is this correct? Should I have a different id for different subfeeds?
		return obj.uuid
	
	def description(self, obj):
		return obj.description
	
	# Would this be meaningful? I think it's just ignored anyway, for ical format.
	#def categories(self, obj):
	#	event_ct = ContentType.objects.get_for_model(Event)
	#	event_pks = obj.events.values_list('pk')
	#	return [tag.name for tag in Tag.objects.filter(content_type=event_ct, object_id__in=event_pks)]
	
	def item_title(self, item):
		return item.name
	
	def item_description(self, item):
		return item.description
	
	def item_link(self, item):
		return self.reverse(item)
	
	def item_guid(self, item):
		return item.uuid
	
	def item_author_name(self, item):
		if item.owner:
			return item.owner.get_full_name()
	
	def item_author_email(self, item):
		return getattr(item.owner, 'email', None) or None
	
	def item_pubdate(self, item):
		return item.created
	
	def item_categories(self, item):
		return [tag.name for tag in item.tags.all()]
	
	def item_extra_kwargs(self, item):
		return {
			'start': item.get_start(),
			'end': item.get_end(),
			'last_modified': item.last_modified,
			# Is forcing unicode enough, or should we look for a "custom method"?
			'location': force_unicode(item.location),
		}
	
	class Meta:
		verbose_name = "iCalendar view"

field = ICalendarFeedView._meta.get_field('feed_type')
field._choices += ((ICALENDAR, 'iCalendar'),)
field.default = ICALENDAR