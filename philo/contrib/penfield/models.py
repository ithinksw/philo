from datetime import date, datetime

from django.conf import settings
from django.conf.urls.defaults import url, patterns, include
from django.contrib.sites.models import Site, RequestSite
from django.contrib.syndication.views import add_domain
from django.db import models
from django.http import Http404, HttpResponse
from django.template import RequestContext, Template as DjangoTemplate
from django.utils import feedgenerator, tzinfo
from django.utils.datastructures import SortedDict
from django.utils.encoding import smart_unicode, force_unicode
from django.utils.html import escape

from philo.contrib.penfield.exceptions import HttpNotAcceptable
from philo.contrib.penfield.middleware import http_not_acceptable
from philo.contrib.penfield.validators import validate_pagination_count
from philo.exceptions import ViewCanNotProvideSubpath
from philo.models import Tag, Entity, MultiView, Page, register_value_model, TemplateField, Template
from philo.utils import paginate

try:
	import mimeparse
except:
	mimeparse = None


ATOM = feedgenerator.Atom1Feed.mime_type
RSS = feedgenerator.Rss201rev2Feed.mime_type
FEEDS = SortedDict([
	(ATOM, feedgenerator.Atom1Feed),
	(RSS, feedgenerator.Rss201rev2Feed),
])
FEED_CHOICES = (
	(ATOM, "Atom"),
	(RSS, "RSS"),
)


class FeedView(MultiView):
	"""
	The FeedView expects to handle a number of different feeds for the
	same object - i.e. patterns for a blog to handle all entries or
	just entries for a certain year/month/day.
	
	This class would subclass django.contrib.syndication.views.Feed, but
	that would make it callable, which causes problems.
	"""
	feed_type = models.CharField(max_length=50, choices=FEED_CHOICES, default=ATOM)
	feed_suffix = models.CharField(max_length=255, blank=False, default="feed")
	feeds_enabled = models.BooleanField(default=True)
	feed_length = models.PositiveIntegerField(blank=True, null=True, default=15, help_text="The maximum number of items to return for this feed. All items will be returned if this field is blank.")
	
	item_title_template = models.ForeignKey(Template, blank=True, null=True, related_name="%(app_label)s_%(class)s_title_related")
	item_description_template = models.ForeignKey(Template, blank=True, null=True, related_name="%(app_label)s_%(class)s_description_related")
	
	item_context_var = 'items'
	object_attr = 'object'
	
	description = ""
	
	def feed_patterns(self, base, get_items_attr, page_attr, reverse_name):
		"""
		Given the name to be used to reverse this view and the names of
		the attributes for the function that fetches the objects, returns
		patterns suitable for inclusion in urlpatterns.
		"""
		urlpatterns = patterns('')
		if self.feeds_enabled:
			feed_reverse_name = "%s_feed" % reverse_name
			feed_view = http_not_acceptable(self.feed_view(get_items_attr, feed_reverse_name))
			feed_pattern = r'%s%s%s$' % (base, (base and base[-1] != "^") and "/" or "", self.feed_suffix)
			urlpatterns += patterns('',
				url(feed_pattern, feed_view, name=feed_reverse_name),
			)
		urlpatterns += patterns('',
			url(r"%s$" % base, self.page_view(get_items_attr, page_attr), name=reverse_name)
		)
		return urlpatterns
	
	def get_object(self, request, **kwargs):
		return getattr(self, self.object_attr)
	
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
			return response
		
		return inner
	
	def page_view(self, get_items_attr, page_attr):
		"""
		Returns a view function that renders a list of items as a page.
		"""
		get_items = callable(get_items_attr) and get_items_attr or getattr(self, get_items_attr)
		page = isinstance(page_attr, Page) and page_attr or getattr(self, page_attr)
		
		def inner(request, extra_context=None, *args, **kwargs):
			items, extra_context = get_items(request, extra_context=extra_context, *args, **kwargs)
			items, item_context = self.process_page_items(request, items)
			
			context = self.get_context()
			context.update(extra_context or {})
			context.update(item_context or {})
			
			return page.render_to_response(request, extra_context=context)
		return inner
	
	def process_page_items(self, request, items):
		"""
		Hook for handling any extra processing of items based on a
		request, such as pagination or searching. This method is
		expected to return a list of items and a dictionary to be
		added to the page context.
		"""
		item_context = {
			self.item_context_var: items
		}
		return items, item_context
	
	def get_feed_type(self, request):
		feed_type = self.feed_type
		if feed_type not in FEEDS:
			feed_type = FEEDS.keys()[0]
		accept = request.META.get('HTTP_ACCEPT')
		if accept and feed_type not in accept and "*/*" not in accept and "%s/*" % feed_type.split("/")[0] not in accept:
			# Wups! They aren't accepting the chosen format. Is there another format we can use?
			if mimeparse:
				feed_type = mimeparse.best_match(FEEDS.keys(), accept)
			else:
				for feed_type in FEEDS.keys():
					if feed_type in accept or "%s/*" % feed_type.split("/")[0] in accept:
						break
				else:
					feed_type = None
			if not feed_type:
				raise HttpNotAcceptable
		return FEEDS[feed_type]
	
	def get_feed(self, obj, request, reverse_name):
		"""
		Returns an unpopulated feedgenerator.DefaultFeed object for this object.
		"""
		try:
			current_site = Site.objects.get_current()
		except Site.DoesNotExist:
			current_site = RequestSite(request)
		
		feed_type = self.get_feed_type(request)
		node = request.node
		link = node.get_absolute_url(with_domain=True, request=request, secure=request.is_secure())
		
		feed = feed_type(
			title = self.__get_dynamic_attr('title', obj),
			subtitle = self.__get_dynamic_attr('subtitle', obj),
			link = link,
			description = self.__get_dynamic_attr('description', obj),
			language = settings.LANGUAGE_CODE.decode(),
			feed_url = add_domain(
				current_site.domain,
				self.__get_dynamic_attr('feed_url', obj) or node.construct_url(node.subpath, with_domain=True, request=request, secure=request.is_secure()),
				request.is_secure()
			),
			author_name = self.__get_dynamic_attr('author_name', obj),
			author_link = self.__get_dynamic_attr('author_link', obj),
			author_email = self.__get_dynamic_attr('author_email', obj),
			categories = self.__get_dynamic_attr('categories', obj),
			feed_copyright = self.__get_dynamic_attr('feed_copyright', obj),
			feed_guid = self.__get_dynamic_attr('feed_guid', obj),
			ttl = self.__get_dynamic_attr('ttl', obj),
			**self.feed_extra_kwargs(obj)
		)
		return feed
	
	def populate_feed(self, feed, items, request):
		if self.item_title_template:
			title_template = DjangoTemplate(self.item_title_template.code)
		else:
			title_template = None
		if self.item_description_template:
			description_template = DjangoTemplate(self.item_description_template.code)
		else:
			description_template = None
		
		node = request.node
		try:
			current_site = Site.objects.get_current()
		except Site.DoesNotExist:
			current_site = RequestSite(request)
		
		if self.feed_length is not None:
			items = items[:self.feed_length]
		
		for item in items:
			if title_template is not None:
				title = title_template.render(RequestContext(request, {'obj': item}))
			else:
				title = self.__get_dynamic_attr('item_title', item)
			if description_template is not None:
				description = description_template.render(RequestContext(request, {'obj': item}))
			else:
				description = self.__get_dynamic_attr('item_description', item)
			
			link = node.construct_url(self.reverse(obj=item), with_domain=True, request=request, secure=request.is_secure())
			
			enc = None
			enc_url = self.__get_dynamic_attr('item_enclosure_url', item)
			if enc_url:
				enc = feedgenerator.Enclosure(
					url = smart_unicode(add_domain(
							current_site.domain,
							enc_url,
							request.is_secure()
					)),
					length = smart_unicode(self.__get_dynamic_attr('item_enclosure_length', item)),
					mime_type = smart_unicode(self.__get_dynamic_attr('item_enclosure_mime_type', item))
				)
			author_name = self.__get_dynamic_attr('item_author_name', item)
			if author_name is not None:
				author_email = self.__get_dynamic_attr('item_author_email', item)
				author_link = self.__get_dynamic_attr('item_author_link', item)
			else:
				author_email = author_link = None
			
			pubdate = self.__get_dynamic_attr('item_pubdate', item)
			if pubdate and not pubdate.tzinfo:
				ltz = tzinfo.LocalTimezone(pubdate)
				pubdate = pubdate.replace(tzinfo=ltz)
			
			feed.add_item(
				title = title,
				link = link,
				description = description,
				unique_id = self.__get_dynamic_attr('item_guid', item, link),
				enclosure = enc,
				pubdate = pubdate,
				author_name = author_name,
				author_email = author_email,
				author_link = author_link,
				categories = self.__get_dynamic_attr('item_categories', item),
				item_copyright = self.__get_dynamic_attr('item_copyright', item),
				**self.item_extra_kwargs(item)
			)
	
	def __get_dynamic_attr(self, attname, obj, default=None):
		try:
			attr = getattr(self, attname)
		except AttributeError:
			return default
		if callable(attr):
			# Check func_code.co_argcount rather than try/excepting the
			# function and catching the TypeError, because something inside
			# the function may raise the TypeError. This technique is more
			# accurate.
			if hasattr(attr, 'func_code'):
				argcount = attr.func_code.co_argcount
			else:
				argcount = attr.__call__.func_code.co_argcount
			if argcount == 2: # one argument is 'self'
				return attr(obj)
			else:
				return attr()
		return attr
	
	def feed_extra_kwargs(self, obj):
		"""
		Returns an extra keyword arguments dictionary that is used when
		initializing the feed generator.
		"""
		return {}
	
	def item_extra_kwargs(self, item):
		"""
		Returns an extra keyword arguments dictionary that is used with
		the `add_item` call of the feed generator.
		"""
		return {}
	
	def item_title(self, item):
		return escape(force_unicode(item))
	
	def item_description(self, item):
		return force_unicode(item)
	
	class Meta:
		abstract=True


class Blog(Entity):
	title = models.CharField(max_length=255)
	slug = models.SlugField(max_length=255)
	
	def __unicode__(self):
		return self.title
	
	@property
	def entry_tags(self):
		""" Returns a QuerySet of Tags that are used on any entries in this blog. """
		return Tag.objects.filter(blogentries__blog=self).distinct()
	
	@property
	def entry_dates(self):
		dates = {'year': self.entries.dates('date', 'year', order='DESC'), 'month': self.entries.dates('date', 'month', order='DESC'), 'day': self.entries.dates('date', 'day', order='DESC')}
		return dates


register_value_model(Blog)


class BlogEntry(Entity):
	title = models.CharField(max_length=255)
	slug = models.SlugField(max_length=255)
	blog = models.ForeignKey(Blog, related_name='entries', blank=True, null=True)
	author = models.ForeignKey(getattr(settings, 'PHILO_PERSON_MODULE', 'auth.User'), related_name='blogentries')
	date = models.DateTimeField(default=None)
	content = models.TextField()
	excerpt = models.TextField(blank=True, null=True)
	tags = models.ManyToManyField(Tag, related_name='blogentries', blank=True, null=True)
	
	def save(self, *args, **kwargs):
		if self.date is None:
			self.date = datetime.now()
		super(BlogEntry, self).save(*args, **kwargs)
	
	def __unicode__(self):
		return self.title
	
	class Meta:
		ordering = ['-date']
		verbose_name_plural = "blog entries"
		get_latest_by = "date"


register_value_model(BlogEntry)


class BlogView(FeedView):
	ENTRY_PERMALINK_STYLE_CHOICES = (
		('D', 'Year, month, and day'),
		('M', 'Year and month'),
		('Y', 'Year'),
		('B', 'Custom base'),
		('N', 'No base')
	)
	
	blog = models.ForeignKey(Blog, related_name='blogviews')
	
	index_page = models.ForeignKey(Page, related_name='blog_index_related')
	entry_page = models.ForeignKey(Page, related_name='blog_entry_related')
	# TODO: entry_archive is misleading. Rename to ymd_page or timespan_page.
	entry_archive_page = models.ForeignKey(Page, related_name='blog_entry_archive_related', null=True, blank=True)
	tag_page = models.ForeignKey(Page, related_name='blog_tag_related')
	tag_archive_page = models.ForeignKey(Page, related_name='blog_tag_archive_related', null=True, blank=True)
	entries_per_page = models.IntegerField(blank=True, validators=[validate_pagination_count], null=True)
	
	entry_permalink_style = models.CharField(max_length=1, choices=ENTRY_PERMALINK_STYLE_CHOICES)
	entry_permalink_base = models.CharField(max_length=255, blank=False, default='entries')
	tag_permalink_base = models.CharField(max_length=255, blank=False, default='tags')
	
	item_context_var = 'entries'
	object_attr = 'blog'
	
	def __unicode__(self):
		return u'BlogView for %s' % self.blog.title
	
	def get_reverse_params(self, obj):
		if isinstance(obj, BlogEntry):
			if obj.blog == self.blog:
				kwargs = {'slug': obj.slug}
				if self.entry_permalink_style in 'DMY':
					kwargs.update({'year': str(obj.date.year).zfill(4)})
					if self.entry_permalink_style in 'DM':
						kwargs.update({'month': str(obj.date.month).zfill(2)})
						if self.entry_permalink_style == 'D':
							kwargs.update({'day': str(obj.date.day).zfill(2)})
				return self.entry_view, [], kwargs
		elif isinstance(obj, Tag) or (isinstance(obj, models.query.QuerySet) and obj.model == Tag and obj):
			if isinstance(obj, Tag):
				obj = [obj]
			slugs = [tag.slug for tag in obj if tag in self.get_tag_queryset()]
			if slugs:
				return 'entries_by_tag', [], {'tag_slugs': "/".join(slugs)}
		elif isinstance(obj, (date, datetime)):
			kwargs = {
				'year': str(obj.year).zfill(4),
				'month': str(obj.month).zfill(2),
				'day': str(obj.day).zfill(2)
			}
			return 'entries_by_day', [], kwargs
		raise ViewCanNotProvideSubpath
	
	@property
	def urlpatterns(self):
		urlpatterns = self.feed_patterns(r'^', 'get_all_entries', 'index_page', 'index') +\
			self.feed_patterns(r'^%s/(?P<tag_slugs>[-\w]+[-+/\w]*)$' % self.tag_permalink_base, 'get_entries_by_tag', 'tag_page', 'entries_by_tag')
		
		if self.tag_archive_page:
			urlpatterns += patterns('',
				url((r'^%s$' % self.tag_permalink_base), self.tag_archive_view, name='tag_archive')
			)
		
		if self.entry_archive_page:
			if self.entry_permalink_style in 'DMY':
				urlpatterns += self.feed_patterns(r'^(?P<year>\d{4})', 'get_entries_by_ymd', 'entry_archive_page', 'entries_by_year')
				if self.entry_permalink_style in 'DM':
					urlpatterns += self.feed_patterns(r'^(?P<year>\d{4})/(?P<month>\d{2})', 'get_entries_by_ymd', 'entry_archive_page', 'entries_by_month')
					if self.entry_permalink_style == 'D':
						urlpatterns += self.feed_patterns(r'^(?P<year>\d{4})/(?P<month>\d{2})/(?P<day>\d{2})', 'get_entries_by_ymd', 'entry_archive_page', 'entries_by_day')
		
		if self.entry_permalink_style == 'D':
			urlpatterns += patterns('',
				url(r'^(?P<year>\d{4})/(?P<month>\d{2})/(?P<day>\d{2})/(?P<slug>[-\w]+)$', self.entry_view)
			)
		elif self.entry_permalink_style == 'M':
			urlpatterns += patterns('',
				url(r'^(?P<year>\d{4})/(?P<month>\d{2})/(?P<slug>[-\w]+)$', self.entry_view)
			)
		elif self.entry_permalink_style == 'Y':
			urlpatterns += patterns('',
				url(r'^(?P<year>\d{4})/(?P<slug>[-\w]+)$', self.entry_view)
			)
		elif self.entry_permalink_style == 'B':
			urlpatterns += patterns('',
				url((r'^%s/(?P<slug>[-\w]+)$' % self.entry_permalink_base), self.entry_view)
			)
		else:
			urlpatterns = patterns('',
				url(r'^(?P<slug>[-\w]+)$', self.entry_view)
			)
		return urlpatterns
	
	def get_context(self):
		return {'blog': self.blog}
	
	def get_entry_queryset(self):
		return self.blog.entries.all()
	
	def get_tag_queryset(self):
		return self.blog.entry_tags
	
	def get_all_entries(self, request, extra_context=None):
		return self.get_entry_queryset(), extra_context
	
	def get_entries_by_ymd(self, request, year=None, month=None, day=None, extra_context=None):
		if not self.entry_archive_page:
			raise Http404
		entries = self.get_entry_queryset()
		if year:
			entries = entries.filter(date__year=year)
		if month:
			entries = entries.filter(date__month=month)
		if day:
			entries = entries.filter(date__day=day)
		
		context = extra_context or {}
		context.update({'year': year, 'month': month, 'day': day})
		return entries, context
	
	def get_entries_by_tag(self, request, tag_slugs, extra_context=None):
		tag_slugs = tag_slugs.replace('+', '/').split('/')
		tags = self.get_tag_queryset().filter(slug__in=tag_slugs)
		
		if not tags:
			raise Http404
		
		# Raise a 404 on an incorrect slug.
		found_slugs = [tag.slug for tag in tags]
		for slug in tag_slugs:
			if slug and slug not in found_slugs:
				raise Http404

		entries = self.get_entry_queryset()
		for tag in tags:
			entries = entries.filter(tags=tag)
		
		context = extra_context or {}
		context.update({'tags': tags})
		
		return entries, context
	
	def entry_view(self, request, slug, year=None, month=None, day=None, extra_context=None):
		entries = self.get_entry_queryset()
		if year:
			entries = entries.filter(date__year=year)
		if month:
			entries = entries.filter(date__month=month)
		if day:
			entries = entries.filter(date__day=day)
		try:
			entry = entries.get(slug=slug)
		except:
			raise Http404
		context = self.get_context()
		context.update(extra_context or {})
		context.update({'entry': entry})
		return self.entry_page.render_to_response(request, extra_context=context)
	
	def tag_archive_view(self, request, extra_context=None):
		if not self.tag_archive_page:
			raise Http404
		context = self.get_context()
		context.update(extra_context or {})
		context.update({
			'tags': self.get_tag_queryset()
		})
		return self.tag_archive_page.render_to_response(request, extra_context=context)
	
	def feed_view(self, get_items_attr, reverse_name):
		get_items = callable(get_items_attr) and get_items_attr or getattr(self, get_items_attr)
		
		def inner(request, extra_context=None, *args, **kwargs):
			obj = self.get_object(request, *args, **kwargs)
			feed = self.get_feed(obj, request, reverse_name)
			items, extra_context = get_items(request, extra_context=extra_context, *args, **kwargs)
			self.populate_feed(feed, items, request)
			
			if 'tags' in extra_context:
				tags = extra_context['tags']
				feed.feed['link'] = request.node.construct_url(self.reverse(obj=tags), with_domain=True, request=request, secure=request.is_secure())
			else:
				tags = obj.entry_tags
			
			feed.feed['categories'] = [tag.name for tag in tags]
			
			response = HttpResponse(mimetype=feed.mime_type)
			feed.write(response, 'utf-8')
			return response
		
		return inner
	
	def process_page_items(self, request, items):
		if self.entries_per_page:
			page_num = request.GET.get('page', 1)
			paginator, paginated_page, items = paginate(items, self.entries_per_page, page_num)
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
	
	def title(self, obj):
		return obj.title
	
	def item_title(self, item):
		return item.title
	
	def item_description(self, item):
		return item.content
	
	def item_author_name(self, item):
		return item.author.get_full_name()
	
	def item_pubdate(self, item):
		return item.date
	
	def item_categories(self, item):
		return [tag.name for tag in item.tags.all()]


class Newsletter(Entity):
	title = models.CharField(max_length=255)
	slug = models.SlugField(max_length=255)
	
	def __unicode__(self):
		return self.title


register_value_model(Newsletter)


class NewsletterArticle(Entity):
	title = models.CharField(max_length=255)
	slug = models.SlugField(max_length=255)
	newsletter = models.ForeignKey(Newsletter, related_name='articles')
	authors = models.ManyToManyField(getattr(settings, 'PHILO_PERSON_MODULE', 'auth.User'), related_name='newsletterarticles')
	date = models.DateTimeField(default=None)
	lede = TemplateField(null=True, blank=True, verbose_name='Summary')
	full_text = TemplateField(db_index=True)
	tags = models.ManyToManyField(Tag, related_name='newsletterarticles', blank=True, null=True)
	
	def save(self, *args, **kwargs):
		if self.date is None:
			self.date = datetime.now()
		super(NewsletterArticle, self).save(*args, **kwargs)
	
	def __unicode__(self):
		return self.title
	
	class Meta:
		get_latest_by = 'date'
		ordering = ['-date']
		unique_together = (('newsletter', 'slug'),)


register_value_model(NewsletterArticle)


class NewsletterIssue(Entity):
	title = models.CharField(max_length=255)
	slug = models.SlugField(max_length=255)
	newsletter = models.ForeignKey(Newsletter, related_name='issues')
	numbering = models.CharField(max_length=50, help_text='For example, 04.02 for volume 4, issue 2.')
	articles = models.ManyToManyField(NewsletterArticle, related_name='issues')
	
	def __unicode__(self):
		return self.title
	
	class Meta:
		ordering = ['-numbering']
		unique_together = (('newsletter', 'numbering'),)


register_value_model(NewsletterIssue)


class NewsletterView(FeedView):
	ARTICLE_PERMALINK_STYLE_CHOICES = (
		('D', 'Year, month, and day'),
		('M', 'Year and month'),
		('Y', 'Year'),
		('S', 'Slug only')
	)
	
	newsletter = models.ForeignKey(Newsletter, related_name='newsletterviews')
	
	index_page = models.ForeignKey(Page, related_name='newsletter_index_related')
	article_page = models.ForeignKey(Page, related_name='newsletter_article_related')
	article_archive_page = models.ForeignKey(Page, related_name='newsletter_article_archive_related', null=True, blank=True)
	issue_page = models.ForeignKey(Page, related_name='newsletter_issue_related')
	issue_archive_page = models.ForeignKey(Page, related_name='newsletter_issue_archive_related', null=True, blank=True)
	
	article_permalink_style = models.CharField(max_length=1, choices=ARTICLE_PERMALINK_STYLE_CHOICES)
	article_permalink_base = models.CharField(max_length=255, blank=False, default='articles')
	issue_permalink_base = models.CharField(max_length=255, blank=False, default='issues')
	
	item_context_var = 'articles'
	object_attr = 'newsletter'
	
	def __unicode__(self):
		return "NewsletterView for %s" % self.newsletter.__unicode__()
	
	def get_reverse_params(self, obj):
		if isinstance(obj, NewsletterArticle):
			if obj.newsletter == self.newsletter:
				kwargs = {'slug': obj.slug}
				if self.article_permalink_style in 'DMY':
					kwargs.update({'year': str(obj.date.year).zfill(4)})
					if self.article_permalink_style in 'DM':
						kwargs.update({'month': str(obj.date.month).zfill(2)})
						if self.article_permalink_style == 'D':
							kwargs.update({'day': str(obj.date.day).zfill(2)})
				return self.article_view, [], kwargs
		elif isinstance(obj, NewsletterIssue):
			if obj.newsletter == self.newsletter:
				return 'issue', [], {'numbering': obj.numbering}
		elif isinstance(obj, (date, datetime)):
			kwargs = {
				'year': str(obj.year).zfill(4),
				'month': str(obj.month).zfill(2),
				'day': str(obj.day).zfill(2)
			}
			return 'articles_by_day', [], kwargs
		raise ViewCanNotProvideSubpath
	
	@property
	def urlpatterns(self):
		urlpatterns = self.feed_patterns(r'^', 'get_all_articles', 'index_page', 'index') + patterns('',
			url(r'^%s/(?P<numbering>.+)$' % self.issue_permalink_base, self.page_view('get_articles_by_issue', 'issue_page'), name='issue')
		)
		if self.issue_archive_page:
			urlpatterns += patterns('',
				url(r'^%s$' % self.issue_permalink_base, self.issue_archive_view, 'issue_archive')
			)
		if self.article_archive_page:
			urlpatterns += patterns('',
				url(r'^%s' % self.article_permalink_base, include(self.feed_patterns('get_all_articles', 'article_archive_page', 'articles')))
			)
			if self.article_permalink_style in 'DMY':
				urlpatterns += self.feed_patterns(r'^%s/(?P<year>\d{4})' % self.article_permalink_base, 'get_articles_by_ymd', 'article_archive_page', 'articles_by_year')
				if self.article_permalink_style in 'DM':
					urlpatterns += self.feed_patterns(r'^%s/(?P<year>\d{4})/(?P<month>\d{2})' % self.article_permalink_base, 'get_articles_by_ymd', 'article_archive_page', 'articles_by_month')
					if self.article_permalink_style == 'D':
						urlpatterns += self.feed_patterns(r'^%s/(?P<year>\d{4})/(?P<month>\d{2})/(?P<day>\d{2})' % self.article_permalink_base, 'get_articles_by_ymd', 'article_archive_page', 'articles_by_day')
		
		if self.article_permalink_style == 'Y':
			urlpatterns += patterns('',
				url(r'^%s/(?P<year>\d{4})/(?P<slug>[\w-]+)$' % self.article_permalink_base, self.article_view)
			)
		elif self.article_permalink_style == 'M':
			urlpatterns += patterns('',
				url(r'^%s/(?P<year>\d{4})/(?P<month>\d{2})/(?P<slug>[\w-]+)$' % self.article_permalink_base, self.article_view)
			)
		elif self.article_permalink_style == 'D':
			urlpatterns += patterns('',
				url(r'^%s/(?P<year>\d{4})/(?P<month>\d{2})/(?P<day>\d{2})/(?P<slug>[\w-]+)$' % self.article_permalink_base, self.article_view)
			)
		else:	
			urlpatterns += patterns('',
				url(r'^%s/(?P<slug>[-\w]+)$' % self.article_permalink_base, self.article_view)
			)
		
		return urlpatterns
	
	def get_context(self):
		return {'newsletter': self.newsletter}
	
	def get_article_queryset(self):
		return self.newsletter.articles.all()
	
	def get_issue_queryset(self):
		return self.newsletter.issues.all()
	
	def get_all_articles(self, request, extra_context=None):
		return self.get_article_queryset(), extra_context
	
	def get_articles_by_ymd(self, request, year, month=None, day=None, extra_context=None):
		articles = self.get_article_queryset().filter(date__year=year)
		if month:
			articles = articles.filter(date__month=month)
		if day:
			articles = articles.filter(date__day=day)
		return articles, extra_context
	
	def get_articles_by_issue(self, request, numbering, extra_context=None):
		try:
			issue = self.get_issue_queryset().get(numbering=numbering)
		except NewsletterIssue.DoesNotExist:
			raise Http404
		context = extra_context or {}
		context.update({'issue': issue})
		return self.get_article_queryset().filter(issues=issue), context
	
	def article_view(self, request, slug, year=None, month=None, day=None, extra_context=None):
		articles = self.get_article_queryset()
		if year:
			articles = articles.filter(date__year=year)
		if month:
			articles = articles.filter(date__month=month)
		if day:
			articles = articles.filter(date__day=day)
		try:
			article = articles.get(slug=slug)
		except NewsletterArticle.DoesNotExist:
			raise Http404
		context = self.get_context()
		context.update(extra_context or {})
		context.update({'article': article})
		return self.article_page.render_to_response(request, extra_context=context)
	
	def issue_archive_view(self, request, extra_context):
		if not self.issue_archive_page:
			raise Http404
		context = self.get_context()
		context.update(extra_context or {})
		context.update({
			'issues': self.get_issue_queryset()
		})
		return self.issue_archive_page.render_to_response(request, extra_context=context)
	
	def title(self, obj):
		return obj.title
	
	def item_title(self, item):
		return item.title
	
	def item_description(self, item):
		return item.full_text
	
	def item_author_name(self, item):
		authors = list(item.authors.all())
		if len(authors) > 1:
			return "%s and %s" % (", ".join([author.get_full_name() for author in authors[:-1]]), authors[-1].get_full_name())
		elif authors:
			return authors[0].get_full_name()
		else:
			return ''
	
	def item_pubdate(self, item):
		return item.date
	
	def item_categories(self, item):
		return [tag.name for tag in item.tags.all()]