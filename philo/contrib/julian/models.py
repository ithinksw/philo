import calendar
import datetime

from django.conf import settings
from django.conf.urls.defaults import url, patterns, include
from django.contrib.auth.models import User
from django.contrib.contenttypes.generic import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.models import Site
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.core.validators import RegexValidator
from django.db import models
from django.db.models.query import QuerySet
from django.http import HttpResponse, Http404
from django.utils.encoding import force_unicode
from taggit.managers import TaggableManager

from philo.contrib.julian.feedgenerator import ICalendarFeed
from philo.contrib.winer.models import FeedView
from philo.contrib.winer.feeds import registry
from philo.exceptions import ViewCanNotProvideSubpath
from philo.models import Tag, Entity, Page
from philo.models.fields import TemplateField
from philo.utils import ContentTypeRegistryLimiter


__all__ = ('register_location_model', 'unregister_location_model', 'Location', 'TimedModel', 'Event', 'Calendar', 'CalendarView',)


registry.register(ICalendarFeed, verbose_name="iCalendar")
try:
	DEFAULT_SITE = Site.objects.get_current()
except:
	DEFAULT_SITE = None
_languages = dict(settings.LANGUAGES)
try:
	_languages[settings.LANGUAGE_CODE]
	DEFAULT_LANGUAGE = settings.LANGUAGE_CODE
except KeyError:
	try:
		lang = settings.LANGUAGE_CODE.split('-')[0]
		_languages[lang]
		DEFAULT_LANGUAGE = lang
	except KeyError:
		DEFAULT_LANGUAGE = None


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
		return datetime.datetime.combine(self.start_date, self.start_time) if self.start_time else self.start_date
	
	def get_end(self):
		return datetime.datetime.combine(self.end_date, self.end_time) if self.end_time else self.end_date
	
	class Meta:
		abstract = True


class EventManager(models.Manager):
	def get_query_set(self):
		return EventQuerySet(self.model)

class EventQuerySet(QuerySet):
	def upcoming(self):
		return self.filter(start_date__gte=datetime.date.today())
	def current(self):
		return self.filter(start_date__lte=datetime.date.today(), end_date__gte=datetime.date.today())
	def single_day(self):
		return self.filter(start_date__exact=models.F('end_date'))
	def multiday(self):
		return self.exclude(start_date__exact=models.F('end_date'))

class Event(Entity, TimedModel):
	name = models.CharField(max_length=255)
	slug = models.SlugField(max_length=255, unique_for_date='start_date')
	
	location_content_type = models.ForeignKey(ContentType, limit_choices_to=location_content_type_limiter, blank=True, null=True)
	location_pk = models.TextField(blank=True)
	location = GenericForeignKey('location_content_type', 'location_pk')
	
	description = TemplateField()
	
	tags = models.ManyToManyField(Tag, related_name='events', blank=True, null=True)
	
	parent_event = models.ForeignKey('self', blank=True, null=True)
	
	# TODO: "User module"
	owner = models.ForeignKey(User, related_name='owned_events')
	
	created = models.DateTimeField(auto_now_add=True)
	last_modified = models.DateTimeField(auto_now=True)
	
	site = models.ForeignKey(Site, default=DEFAULT_SITE)
	
	@property
	def uuid(self):
		return "%s@%s" % (self.created.isoformat(), getattr(self.site, 'domain', 'None'))
	
	objects = EventManager()
	
	def __unicode__(self):
		return self.name
	
	class Meta:
		unique_together = ('site', 'created')


class Calendar(Entity):
	name = models.CharField(max_length=100)
	slug = models.SlugField(max_length=100)
	description = models.TextField(blank=True)
	events = models.ManyToManyField(Event, related_name='calendars', blank=True)
	
	site = models.ForeignKey(Site, default=DEFAULT_SITE)
	language = models.CharField(max_length=5, choices=settings.LANGUAGES, default=DEFAULT_LANGUAGE)
	
	def __unicode__(self):
		return self.name
	
	@property
	def fpi(self):
		# See http://xml.coverpages.org/tauber-fpi.html or ISO 9070:1991 for format information.
		return "-//%s//%s//%s" % (self.site.name, self.name, self.language.split('-')[0].upper())
	
	class Meta:
		unique_together = ('name', 'site', 'language')


class CalendarView(FeedView):
	calendar = models.ForeignKey(Calendar)
	index_page = models.ForeignKey(Page, related_name="calendar_index_related")
	event_detail_page = models.ForeignKey(Page, related_name="calendar_detail_related")
	
	timespan_page = models.ForeignKey(Page, related_name="calendar_timespan_related", blank=True, null=True)
	tag_page = models.ForeignKey(Page, related_name="calendar_tag_related", blank=True, null=True)
	location_page = models.ForeignKey(Page, related_name="calendar_location_related", blank=True, null=True)
	owner_page = models.ForeignKey(Page, related_name="calendar_owner_related", blank=True, null=True)
	
	tag_archive_page = models.ForeignKey(Page, related_name="calendar_tag_archive_related", blank=True, null=True)
	location_archive_page = models.ForeignKey(Page, related_name="calendar_location_archive_related", blank=True, null=True)
	owner_archive_page = models.ForeignKey(Page, related_name="calendar_owner_archive_related", blank=True, null=True)
	
	tag_permalink_base = models.CharField(max_length=30, default='tags')
	owner_permalink_base = models.CharField(max_length=30, default='owners')
	location_permalink_base = models.CharField(max_length=30, default='locations')
	events_per_page = models.PositiveIntegerField(blank=True, null=True)
	
	item_context_var = "events"
	object_attr = "calendar"
	
	def get_reverse_params(self, obj):
		if isinstance(obj, User):
			return 'events_for_user', [], {'username': obj.username}
		elif isinstance(obj, Event):
			return 'event_detail', [], {
				'year': str(obj.start_date.year).zfill(4),
				'month': str(obj.start_date.month).zfill(2),
				'day': str(obj.start_date.day).zfill(2),
				'slug': obj.slug
			}
		elif isinstance(obj, Tag) or isinstance(obj, models.query.QuerySet) and obj.model == Tag:
			if isinstance(obj, Tag):
				obj = [obj]
			return 'entries_by_tag', [], {'tag_slugs': '/'.join(obj)}
		raise ViewCanNotProvideSubpath
	
	def timespan_patterns(self, pattern, timespan_name):
		return self.feed_patterns(pattern, 'get_events_by_timespan', 'timespan_page', "events_by_%s" % timespan_name)
	
	@property
	def urlpatterns(self):
		# Perhaps timespans should be done with GET parameters? Or two /-separated
		# date slugs? (e.g. 2010-02-1/2010-02-2) or a start and duration?
		# (e.g. 2010-02-01/week/ or ?d=2010-02-01&l=week)
		urlpatterns = self.feed_patterns(r'^', 'get_all_events', 'index_page', 'index') + \
			self.timespan_patterns(r'^(?P<year>\d{4})', 'year') + \
			self.timespan_patterns(r'^(?P<year>\d{4})/(?P<month>\d{2})', 'month') + \
			self.timespan_patterns(r'^(?P<year>\d{4})/(?P<month>\d{2})/(?P<day>\d{2})', 'day') + \
			self.feed_patterns(r'^%s/(?P<username>[^/]+)' % self.owner_permalink_base, 'get_events_by_owner', 'owner_page', 'events_by_user') + \
			self.feed_patterns(r'^%s/(?P<app_label>\w+)/(?P<model>\w+)/(?P<pk>[^/]+)' % self.location_permalink_base, 'get_events_by_location', 'location_page', 'events_by_location') + \
			self.feed_patterns(r'^%s/(?P<tag_slugs>[-\w]+[-+/\w]*)' % self.tag_permalink_base, 'get_events_by_tag', 'tag_page', 'events_by_tag') + \
			patterns('',
				url(r'(?P<year>\d{4})/(?P<month>\d{2})/(?P<day>\d{2})/(?P<slug>[\w-]+)$', self.event_detail_view, name="event_detail"),
			)
			
			# Some sort of shortcut for a location would be useful. This could be on a per-calendar
			# or per-calendar-view basis.
			#url(r'^%s/(?P<slug>[\w-]+)' % self.location_permalink_base, ...)
		
		if self.tag_archive_page_id:
			urlpatterns += patterns('',
				url(r'^%s$' % self.tag_permalink_base, self.tag_archive_view, name='tag_archive')
			)
		
		if self.owner_archive_page_id:
			urlpatterns += patterns('',
				url(r'^%s$' % self.owner_permalink_base, self.owner_archive_view, name='owner_archive')
			)
		
		if self.location_archive_page_id:
			urlpatterns += patterns('',
				url(r'^%s$' % self.location_permalink_base, self.location_archive_view, name='location_archive')
			)
		return urlpatterns
	
	# Basic QuerySet fetchers.
	def get_event_queryset(self):
		return self.calendar.events.all()
	
	def get_timespan_queryset(self, year, month=None, day=None):
		qs = self.get_event_queryset()
		# See python documentation for the min/max values.
		if year and month and day:
			year, month, day = int(year), int(month), int(day)
			start_datetime = datetime.datetime(year, month, day, 0, 0)
			end_datetime = datetime.datetime(year, month, day, 23, 59)
		elif year and month:
			year, month = int(year), int(month)
			start_datetime = datetime.datetime(year, month, 1, 0, 0)
			end_datetime = datetime.datetime(year, month, calendar.monthrange(year, month)[1], 23, 59)
		else:
			year = int(year)
			start_datetime = datetime.datetime(year, 1, 1, 0, 0)
			end_datetime = datetime.datetime(year, 12, 31, 23, 59)
		
		return qs.exclude(end_date__lt=start_datetime, end_time__lt=start_datetime).exclude(start_date__gt=end_datetime, start_time__gt=end_datetime, start_time__isnull=False).exclude(start_time__isnull=True, start_date__gt=end_datetime)
	
	def get_tag_queryset(self):
		return Tag.objects.filter(events__calendars=self.calendar).distinct()
	
	def get_location_querysets(self):
		# Potential bottleneck?
		location_map = {}
		locations = Event.objects.values_list('location_content_type', 'location_pk')
		
		for ct, pk in locations:
			location_map.setdefault(ct, []).append(pk)
		
		location_cts = ContentType.objects.in_bulk(location_map.keys())
		location_querysets = {}
		
		for ct_pk, pks in location_map.items():
			ct = location_cts[ct_pk]
			location_querysets[ct] = ct.model_class()._default_manager.filter(pk__in=pks)
		
		return location_querysets
	
	def get_owner_queryset(self):
		return User.objects.filter(owned_events__calendars=self.calendar).distinct()
	
	# Event QuerySet parsers for a request/args/kwargs
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
	
	def get_events_by_owner(self, request, username, extra_context=None):
		try:
			owner = self.get_owner_queryset().get(username=username)
		except User.DoesNotExist:
			raise Http404
		
		qs = self.get_event_queryset().filter(owner=owner)
		context = extra_context or {}
		context.update({
			'owner': owner
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
			ct = ContentType.objects.get_by_natural_key(app_label, model)
			location = ct.model_class()._default_manager.get(pk=pk)
		except ObjectDoesNotExist:
			raise Http404
		
		events = self.get_event_queryset().filter(location_content_type=ct, location_pk=location.pk)
		
		context = extra_context or {}
		context.update({
			'location': location
		})
		return events, context
	
	# Detail View.
	def event_detail_view(self, request, year, month, day, slug, extra_context=None):
		try:
			event = Event.objects.select_related('parent_event').get(start_date__year=year, start_date__month=month, start_date__day=day, slug=slug)
		except Event.DoesNotExist:
			raise Http404
		
		context = self.get_context()
		context.update(extra_context or {})
		context.update({
			'event': event
		})
		return self.event_detail_page.render_to_response(request, extra_context=context)
	
	# Archive Views.
	def tag_archive_view(self, request, extra_context=None):
		tags = self.get_tag_queryset()
		context = self.get_context()
		context.update(extra_context or {})
		context.update({
			'tags': tags
		})
		return self.tag_archive_page.render_to_response(request, extra_context=context)
	
	def location_archive_view(self, request, extra_context=None):
		# What datastructure should locations be?
		locations = self.get_location_querysets()
		context = self.get_context()
		context.update(extra_context or {})
		context.update({
			'locations': locations
		})
		return self.location_archive_page.render_to_response(request, extra_context=context)
	
	def owner_archive_view(self, request, extra_context=None):
		owners = self.get_owner_queryset()
		context = self.get_context()
		context.update(extra_context or {})
		context.update({
			'owners': owners
		})
		return self.owner_archive_page.render_to_response(request, extra_context=context)
	
	# Process page items
	def process_page_items(self, request, items):
		if self.events_per_page:
			page_num = request.GET.get('page', 1)
			paginator, paginated_page, items = paginate(items, self.events_per_page, page_num)
			item_context = {
				'paginator': paginator,
				'paginated_page': paginated_page,
				self.item_context_var: items
			}
		else:
			item_context = {
				self.item_context_var: items
			}
		return items, item_context
	
	# Feed information hooks
	def title(self, obj):
		return obj.name
	
	def link(self, obj):
		# Link is ignored anyway...
		return ""
	
	def feed_guid(self, obj):
		return obj.fpi
	
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
field.default = registry.get_slug(ICalendarFeed, field.default)