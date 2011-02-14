from django.conf import settings
from django.conf.urls.defaults import url, patterns, include
from django.contrib.auth.models import User
from django.contrib.contenttypes.generic import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.core.validators import RegexValidator
from django.db import models
from django.http import HttpResponse, Http404
from django.utils.encoding import force_unicode
from philo.contrib.julian.feedgenerator import ICalendarFeed
from philo.contrib.penfield.models import FeedView, FEEDS
from philo.exceptions import ViewCanNotProvideSubpath
from philo.models import Tag, Entity, Page, TemplateField
from philo.utils import ContentTypeRegistryLimiter
import re, datetime, calendar


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
	slug = models.SlugField(max_length=255, unique=True)
	
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
	slug = models.SlugField(max_length=255, unique_for_date='created')
	
	location_content_type = models.ForeignKey(ContentType, limit_choices_to=location_content_type_limiter, blank=True, null=True)
	location_pk = models.TextField(blank=True)
	location = GenericForeignKey('location_content_type', 'location_pk')
	
	description = TemplateField()
	
	tags = models.ManyToManyField(Tag, related_name='events', blank=True, null=True)
	
	parent_event = models.ForeignKey('self', blank=True, null=True)
	
	# TODO: "User module"
	owner = models.ForeignKey(User)
	
	created = models.DateTimeField(auto_now_add=True)
	last_modified = models.DateTimeField(auto_now=True)
	uuid = models.TextField() # Format?
	
	def __unicode__(self):
		return self.name


class Calendar(Entity):
	name = models.CharField(max_length=100)
	slug = models.SlugField(max_length=100)
	description = models.TextField(blank=True)
	events = models.ManyToManyField(Event, related_name='calendars')
	
	# TODO: Can we auto-generate this on save based on site id and calendar name and settings language?
	uuid = models.TextField("Calendar UUID", unique=True, help_text="Should conform to Formal Public Identifier format. See &lt;http://en.wikipedia.org/wiki/Formal_Public_Identifier&gt;", validators=[RegexValidator(FPI_REGEX)])


class CalendarView(FeedView):
	calendar = models.ForeignKey(Calendar)
	index_page = models.ForeignKey(Page, related_name="calendar_index_related")
	timespan_page = models.ForeignKey(Page, related_name="calendar_timespan_related")
	event_detail_page = models.ForeignKey(Page, related_name="calendar_detail_related")
	tag_page = models.ForeignKey(Page, related_name="calendar_tag_related")
	location_page = models.ForeignKey(Page, related_name="calendar_location_related")
	owner_page = models.ForeignKey(Page, related_name="calendar_owner_related")
	
	tag_archive_page = models.ForeignKey(Page, related_name="calendar_tag_archive_related", blank=True, null=True)
	location_archive_page = models.ForeignKey(Page, related_name="calendar_location_archive_related", blank=True, null=True)
	owner_archive_page = models.ForeignKey(Page, related_name="calendar_owner_archive_related", blank=True, null=True)
	
	tag_permalink_base = models.CharField(max_length=30, default='tags')
	owner_permalink_base = models.CharField(max_length=30, default='owner')
	location_permalink_base = models.CharField(max_length=30, default='location')
	
	item_context_var = "events"
	object_attr = "calendar"
	
	def get_reverse_params(self, obj):
		if isinstance(obj, User):
			return 'events_for_user', [], {'username': obj.username}
		elif isinstance(obj, Event):
			return 'event_detail', [], {
				'year': obj.start_date.year,
				'month': obj.start_date.month,
				'day': obj.start_date.day,
				'slug': obj.slug
			}
		elif isinstance(obj, Tag) or isinstance(obj, models.query.QuerySet) and obj.model == Tag:
			if isinstance(obj, Tag):
				obj = [obj]
			return 'entries_by_tag', [], {'tag_slugs': '/'.join(obj)}
		raise ViewCanNotProvideSubpath
	
	def timespan_patterns(self, timespan_name):
		urlpatterns = patterns('',
		) + self.feed_patterns('get_events_by_timespan', 'timespan_page', "events_by_%s" % timespan_name)
		return urlpatterns
	
	@property
	def urlpatterns(self):
		urlpatterns = patterns('',
			url(r'^', include(self.feed_patterns('get_all_events', 'index_page', 'index'))),
			
			url(r'^(?P<year>\d{4})', include(self.timespan_patterns('year'))),
			url(r'^(?P<year>\d{4})/(?P<month>\d{2})', include(self.timespan_patterns('month'))),
			url(r'^(?P<year>\d{4})/(?P<month>\d{2})/(?P<day>\d{2})', include(self.timespan_patterns('day'))),
			#url(r'^(?P<year>\d{4})/(?P<month>\d{2})/(?P<day>\d{2})/(?P<hour>\d{1,2})', include(self.timespan_patterns('hour'))),
			url(r'(?P<year>\d{4})/(?P<month>\d{2})/(?P<day>\d{2})/(?P<slug>[\w-]+)', self.event_detail_view, name="event_detail"),
			
			url(r'^%s/(?P<username>[^/]+)' % self.owner_permalink_base, include(self.feed_patterns('get_events_by_user', 'owner_page', 'events_by_user'))),
			
			# Some sort of shortcut for a location would be useful. This could be on a per-calendar
			# or per-calendar-view basis.
			#url(r'^%s/(?P<slug>[\w-]+)' % self.location_permalink_base, ...)
			url(r'^%s/(?P<app_label>\w+)/(?P<model>\w+)/(?P<pk>[^/]+)' % self.location_permalink_base, include(self.feed_patterns('get_events_by_location', 'location_page', 'events_by_location'))),
		)
		
		if self.feeds_enabled:
			urlpatterns += patterns('',
				url(r'^%s/(?P<tag_slugs>[-\w]+[-+/\w]*)/%s$' % (self.tag_permalink_base, self.feed_suffix), self.feed_view('get_events_by_tag', 'events_by_tag_feed'), name='events_by_tag_feed'),
			)
		urlpatterns += patterns('',
			url(r'^%s/(?P<tag_slugs>[-\w]+[-+/\w]*)$' % self.tag_permalink_base, self.page_view('get_events_by_tag', 'tag_page'), name='events_by_tag')
		)
		
		if self.tag_archive_page:
			urlpatterns += patterns('',
				url(r'^%s$' % self.tag_permalink_base, self.tag_archive_view, name='tag_archive')
			)
		
		if self.owner_archive_page:
			urlpatterns += patterns('',
				url(r'^%s$' % self.owner_permalink_base, self.owner_archive_view, name='owner_archive')
			)
		
		if self.owner_archive_page:
			urlpatterns += patterns('',
				url(r'^%s$' % self.location_permalink_base, self.location_archive_view, name='location_archive')
			)
		return urlpatterns
	
	def get_event_queryset(self):
		return self.calendar.events.all()
	
	def get_timespan_queryset(self, year, month=None, day=None):
		qs = self.get_event_queryset()
		# See python documentation for the min/max values.
		if year and month and day:
			start_datetime = datetime.datetime(year, month, day, 0, 0)
			end_datetime = datetime.datetime(year, month, day, 23, 59)
		elif year and month:
			start_datetime = datetime.datetime(year, month, 1, 0, 0)
			end_datetime = datetime.datetime(year, month, calendar.monthrange(year, month)[1], 23, 59)
		else:
			start_datetime = datetime.datetime(year, 1, 1, 0, 0)
			end_datetime = datetime.datetime(year, 12, 31, 23, 59)
		
		return qs.exclude(end_date__lt=start_datetime, end_time__lt=start_datetime.time()).exclude(start_date__gt=end_datetime, start_time__gt=end_datetime.time(), start_time__isnull=False).exclude(start_time__isnull=True, start_date__gt=end_datetime.time())
	
	def get_tag_queryset(self):
		return Tag.objects.filter(events__calendar=self.calendar).distinct()
	
	# Event fetchers.
	def get_all_events(self, request, extra_context=None):
		return self.get_event_queryset(), extra_context
	
	def get_events_by_timespan(self, request, year, month=None, day=None, extra_context=None):
		context = extra_context or {}
		context.update({
			'year': year,
			'month': month,
			'day': day
		})
		return self.get_timespan_queryset(year, month, day), context
	
	def get_events_by_user(self, request, username, extra_context=None):
		try:
			user = User.objects.get(username)
		except User.DoesNotExist:
			raise Http404
		
		qs = self.event_queryset().filter(owner=user)
		context = extra_context or {}
		context.update({
			'user': user
		})
		return qs, context
	
	def get_events_by_tag(self, request, tag_slugs, extra_context=None):
		tag_slugs = tag_slugs.replace('+', '/').split('/')
		tags = self.get_tag_queryset().filter(slug__in=tag_slugs)
		
		if not tags:
			raise Http404
		
		# Raise a 404 on an incorrect slug.
		found_slugs = [tag.slug for tag in tags]
		for slug in tag_slugs:
			if slug and slug not in found_slugs:
				raise Http404

		events = self.get_event_queryset()
		for tag in tags:
			events = events.filter(tags=tag)
		
		context = extra_context or {}
		context.update({'tags': tags})
		
		return events, context
	
	def get_events_by_location(self, request, app_label, model, pk, extra_context=None):
		try:
			ct = ContentType.objects.get(app_label=app_label, model=model)
			location = ct.model_class()._default_manager.get(pk=pk)
		except ObjectDoesNotExist:
			raise Http404
		
		events = self.get_event_queryset().filter(location_content_type=ct, location_pk=location.pk)
		
		context = extra_context or {}
		context.update({
			'location': location
		})
		return events, context
	
	# Detail View. TODO: fill this out.
	def event_detail_view(self, request, year, month, day, slug, extra_context=None):
		pass
	
	# Archive Views. TODO: fill these out.
	def tag_archive_view(self, request, extra_context=None):
		pass
	
	def location_archive_view(self, request, extra_context=None):
		pass
	
	def owner_archive_view(self, request, extra_context=None):
		pass
	
	# Feed information hooks
	def title(self, obj):
		return obj.name
	
	def link(self, obj):
		# Link is ignored anyway...
		return ""
	
	def feed_guid(self, obj):
		# Is this correct? Should I have a different id for different subfeeds?
		return obj.uuid
	
	def description(self, obj):
		return obj.description
	
	def feed_extra_kwargs(self, obj):
		return {'filename': "%s.ics" % obj.slug}
	
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
	
	def __unicode__(self):
		return u"%s for %s" % (self.__class__.__name__, self.calendar)

field = CalendarView._meta.get_field('feed_type')
field._choices += ((ICALENDAR, 'iCalendar'),)
field.default = ICALENDAR