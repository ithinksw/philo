# encoding: utf-8
from datetime import date, datetime

from django.conf import settings
from django.conf.urls.defaults import url, patterns, include
from django.db import models
from django.http import Http404, HttpResponse
from taggit.managers import TaggableManager
from taggit.models import Tag, TaggedItem

from philo.contrib.winer.models import FeedView
from philo.exceptions import ViewCanNotProvideSubpath
from philo.models import Entity, Page, register_value_model
from philo.models.fields import TemplateField
from philo.utils import paginate


class Blog(Entity):
	"""Represents a blog which can be posted to."""
	#: The name of the :class:`Blog`, currently called 'title' for historical reasons.
	title = models.CharField(max_length=255)
	
	#: A slug used to identify the :class:`Blog`.
	slug = models.SlugField(max_length=255)
	
	def __unicode__(self):
		return self.title
	
	@property
	def entry_tags(self):
		"""Returns a :class:`QuerySet` of :class:`.Tag`\ s that are used on any entries in this blog."""
		entry_pks = list(self.entries.values_list('pk', flat=True))
		kwargs = {
			'%s__object_id__in' % TaggedItem.tag_relname(): entry_pks
		}
		return TaggedItem.tags_for(BlogEntry).filter(**kwargs)
	
	@property
	def entry_dates(self):
		"""Returns a dictionary of date :class:`QuerySet`\ s for years, months, and days for which there are entries."""
		dates = {'year': self.entries.dates('date', 'year', order='DESC'), 'month': self.entries.dates('date', 'month', order='DESC'), 'day': self.entries.dates('date', 'day', order='DESC')}
		return dates


register_value_model(Blog)


class BlogEntry(Entity):
	"""Represents an entry in a :class:`Blog`."""
	#: The title of the :class:`BlogEntry`.
	title = models.CharField(max_length=255)
	
	#: A slug which identifies the :class:`BlogEntry`.
	slug = models.SlugField(max_length=255)
	
	#: The :class:`Blog` which this entry has been posted to. Can be left blank to represent a "draft" status.
	blog = models.ForeignKey(Blog, related_name='entries', blank=True, null=True)
	
	#: A :class:`ForeignKey` to the author. The model is either :setting:`PHILO_PERSON_MODULE` or :class:`auth.User`.
	author = models.ForeignKey(getattr(settings, 'PHILO_PERSON_MODULE', 'auth.User'), related_name='blogentries')
	
	#: The date and time which the :class:`BlogEntry` is considered posted at.
	date = models.DateTimeField(default=None)
	
	#: The content of the :class:`BlogEntry`.
	content = TemplateField()
	
	#: An optional brief excerpt from the :class:`BlogEntry`.
	excerpt = TemplateField(blank=True, null=True)
	
	#: A ``django-taggit`` :class:`TaggableManager`.
	tags = TaggableManager()
	
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
	"""
	A subclass of :class:`.FeedView` which handles patterns and feeds for a :class:`Blog` and its related :class:`entries <BlogEntry>`.
	
	"""
	ENTRY_PERMALINK_STYLE_CHOICES = (
		('D', 'Year, month, and day'),
		('M', 'Year and month'),
		('Y', 'Year'),
		('B', 'Custom base'),
		('N', 'No base')
	)
	
	#: The :class:`Blog` whose entries should be managed by this :class:`BlogView`
	blog = models.ForeignKey(Blog, related_name='blogviews')
	
	#: The main page of the :class:`Blog` will be rendered with this :class:`.Page`.
	index_page = models.ForeignKey(Page, related_name='blog_index_related')
	#: The detail view of a :class:`BlogEntry` will be rendered with this :class:`Page`.
	entry_page = models.ForeignKey(Page, related_name='blog_entry_related')
	# TODO: entry_archive is misleading. Rename to ymd_page or timespan_page.
	#: Views of :class:`BlogEntry` archives will be rendered with this :class:`Page` (optional).
	entry_archive_page = models.ForeignKey(Page, related_name='blog_entry_archive_related', null=True, blank=True)
	#: Views of :class:`BlogEntry` archives according to their :class:`.Tag`\ s will be rendered with this :class:`Page`.
	tag_page = models.ForeignKey(Page, related_name='blog_tag_related')
	#: The archive of all available tags will be rendered with this :class:`Page` (optional).
	tag_archive_page = models.ForeignKey(Page, related_name='blog_tag_archive_related', null=True, blank=True)
	#: This number will be passed directly into pagination for :class:`BlogEntry` list pages. Pagination will be disabled if this is left blank.
	entries_per_page = models.IntegerField(blank=True, null=True)
	
	#: Depending on the needs of the site, different permalink styles may be appropriate. Example subpaths are provided for a :class:`BlogEntry` posted on May 2nd, 2011 with a slug of "hello". The choices are:
	#: 
	#: 	* Year, month, and day - ``2011/05/02/hello``
	#: 	* Year and month - ``2011/05/hello``
	#: 	* Year - ``2011/hello``
	#: 	* Custom base - :attr:`entry_permalink_base`\ ``/hello``
	#: 	* No base - ``hello``
	entry_permalink_style = models.CharField(max_length=1, choices=ENTRY_PERMALINK_STYLE_CHOICES)
	#: If the :attr:`entry_permalink_style` is set to "Custom base" then the value of this field will be used as the base subpath for year/month/day entry archive pages and entry detail pages. Default: "entries"
	entry_permalink_base = models.CharField(max_length=255, blank=False, default='entries')
	#: This will be used as the base for the views of :attr:`tag_page` and :attr:`tag_archive_page`. Default: "tags"
	tag_permalink_base = models.CharField(max_length=255, blank=False, default='tags')
	
	item_context_var = 'entries'
	
	def __unicode__(self):
		return u'BlogView for %s' % self.blog.title
	
	def get_reverse_params(self, obj):
		if isinstance(obj, BlogEntry):
			if obj.blog_id == self.blog_id:
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
			slugs = [tag.slug for tag in obj if tag in self.get_tag_queryset(self.blog)]
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
		urlpatterns = self.feed_patterns(r'^', 'get_entries', 'index_page', 'index') +\
			self.feed_patterns(r'^%s/(?P<tag_slugs>[-\w]+[-+/\w]*)' % self.tag_permalink_base, 'get_entries', 'tag_page', 'entries_by_tag')
		
		if self.tag_archive_page_id:
			urlpatterns += patterns('',
				url((r'^%s$' % self.tag_permalink_base), self.tag_archive_view, name='tag_archive')
			)
		
		if self.entry_archive_page_id:
			if self.entry_permalink_style in 'DMY':
				urlpatterns += self.feed_patterns(r'^(?P<year>\d{4})', 'get_entries', 'entry_archive_page', 'entries_by_year')
				if self.entry_permalink_style in 'DM':
					urlpatterns += self.feed_patterns(r'^(?P<year>\d{4})/(?P<month>\d{2})', 'get_entries', 'entry_archive_page', 'entries_by_month')
					if self.entry_permalink_style == 'D':
						urlpatterns += self.feed_patterns(r'^(?P<year>\d{4})/(?P<month>\d{2})/(?P<day>\d{2})', 'get_entries', 'entry_archive_page', 'entries_by_day')
		
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
			urlpatterns += patterns('',
				url(r'^(?P<slug>[-\w]+)$', self.entry_view)
			)
		return urlpatterns
	
	def get_entry_queryset(self, obj):
		"""Returns the default :class:`QuerySet` of :class:`BlogEntry` instances for the :class:`BlogView` - all entries that are considered posted in the past. This allows for scheduled posting of entries."""
		return obj.entries.filter(date__lte=datetime.now())
	
	def get_tag_queryset(self, obj):
		"""Returns the default :class:`QuerySet` of :class:`.Tag`\ s for the :class:`BlogView`'s :meth:`get_entries_by_tag` and :meth:`tag_archive_view`."""
		return obj.entry_tags
	
	def get_object(self, request, year=None, month=None, day=None, tag_slugs=None):
		"""Returns a dictionary representing the parameters for a feed which will be exposed."""
		if tag_slugs is None:
			tags = None
		else:
			tag_slugs = tag_slugs.replace('+', '/').split('/')
			tags = self.get_tag_queryset(self.blog).filter(slug__in=tag_slugs)
			if not tags:
				raise Http404
			
			# Raise a 404 on an incorrect slug.
			found_slugs = set([tag.slug for tag in tags])
			for slug in tag_slugs:
				if slug and slug not in found_slugs:
					raise Http404
		
		try:
			if year and month and day:
				context_date = date(int(year), int(month), int(day))
			elif year and month:
				context_date = date(int(year), int(month), 1)
			elif year:
				context_date = date(int(year), 1, 1)
			else:
				context_date = None
		except TypeError, ValueError:
			context_date = None
		
		return {
			'blog': self.blog,
			'tags': tags,
			'year': year,
			'month': month,
			'day': day,
			'date': context_date
		}
	
	def get_entries(self, obj, request, year=None, month=None, day=None, tag_slugs=None, extra_context=None):
		"""Returns the :class:`BlogEntry` objects which will be exposed for the given object, as returned from :meth:`get_object`."""
		entries = self.get_entry_queryset(obj['blog'])
		
		if obj['tags'] is not None:
			tags = obj['tags']
			for tag in tags:
				entries = entries.filter(tags=tag)
		
		if obj['date'] is not None:
			if year:
				entries = entries.filter(date__year=year)
			if month:
				entries = entries.filter(date__month=month)
			if day:
				entries = entries.filter(date__day=day)
		
		context = extra_context or {}
		context.update(obj)
		
		return entries, context
	
	def entry_view(self, request, slug, year=None, month=None, day=None, extra_context=None):
		"""Renders :attr:`entry_page` with the entry specified by the given parameters."""
		entries = self.get_entry_queryset(self.blog)
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
		"""Renders :attr:`tag_archive_page` with the result of :meth:`get_tag_queryset` added to the context."""
		if not self.tag_archive_page:
			raise Http404
		context = self.get_context()
		context.update(extra_context or {})
		context.update({
			'tags': self.get_tag_queryset(self.blog)
		})
		return self.tag_archive_page.render_to_response(request, extra_context=context)
	
	def process_page_items(self, request, items):
		"""Overrides :meth:`.FeedView.process_page_items` to add pagination."""
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
		title = obj['blog'].title
		if obj['tags']:
			title += u" – %s" % u", ".join((tag.name for tag in obj['tags']))
		date = obj['date']
		if date:
			if obj['day']:
				datestr = date.strftime("%F %j, %Y")
			elif obj['month']:
				datestr = date.strftime("%F, %Y")
			elif obj['year']:
				datestr = date.strftime("%Y")
			title += u" – %s" % datestr
		return title
	
	def categories(self, obj):
		tags = obj['tags']
		if tags:
			return (tag.name for tag in tags)
		return None
	
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
	"""Represents a newsletter which will contain :class:`articles <NewsletterArticle>` organized into :class:`issues <NewsletterIssue>`."""
	#: The name of the :class:`Newsletter`, currently callse 'title' for historical reasons.
	title = models.CharField(max_length=255)
	#: A slug used to identify the :class:`Newsletter`.
	slug = models.SlugField(max_length=255)
	
	def __unicode__(self):
		return self.title


register_value_model(Newsletter)


class NewsletterArticle(Entity):
	"""Represents an article in a :class:`Newsletter`"""
	#: The title of the :class:`NewsletterArticle`.
	title = models.CharField(max_length=255)
	#: A slug which identifies the :class:`NewsletterArticle`.
	slug = models.SlugField(max_length=255)
	#: A :class:`ForeignKey` to :class:`Newsletter` representing the newsletter which this article was written for.
	newsletter = models.ForeignKey(Newsletter, related_name='articles')
	#: A :class:`ManyToManyField` to the author(s) of the :class:`NewsletterArticle`. The model is either :setting:`PHILO_PERSON_MODULE` or :class:`auth.User`.
	authors = models.ManyToManyField(getattr(settings, 'PHILO_PERSON_MODULE', 'auth.User'), related_name='newsletterarticles')
	#: The date and time which the :class:`NewsletterArticle` is considered published at.
	date = models.DateTimeField(default=None)
	#: A :class:`.TemplateField` containing an optional short summary of the article, meant to grab a reader's attention and draw them in.
	lede = TemplateField(null=True, blank=True, verbose_name='Summary')
	#: A :class:`.TemplateField` containing the full text of the article.
	full_text = TemplateField(db_index=True)
	#: A ``django-taggit`` :class:`TaggableManager`.
	tags = TaggableManager()
	
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
	"""Represents an issue of the newsletter."""
	#: The title of the :class:`NewsletterIssue`.
	title = models.CharField(max_length=255)
	#: A slug which identifies the :class:`NewsletterIssue`.
	slug = models.SlugField(max_length=255)
	#: A :class:`ForeignKey` to the :class:`Newsletter` which this issue belongs to.
	newsletter = models.ForeignKey(Newsletter, related_name='issues')
	#: The numbering of the issue - for example, 04.02 for volume 4, issue 2. This is an instance of :class:`CharField` to allow any arbitrary numbering system.
	numbering = models.CharField(max_length=50, help_text='For example, 04.02 for volume 4, issue 2.')
	#: A :class:`ManyToManyField` to articles belonging to this issue.
	articles = models.ManyToManyField(NewsletterArticle, related_name='issues')
	
	def __unicode__(self):
		return self.title
	
	class Meta:
		ordering = ['-numbering']
		unique_together = (('newsletter', 'numbering'),)


register_value_model(NewsletterIssue)


class NewsletterView(FeedView):
	"""A subclass of :class:`.FeedView` which handles patterns and feeds for a :class:`Newsletter` and its related :class:`articles <NewsletterArticle>`."""
	ARTICLE_PERMALINK_STYLE_CHOICES = (
		('D', 'Year, month, and day'),
		('M', 'Year and month'),
		('Y', 'Year'),
		('S', 'Slug only')
	)
	
	#: A :class:`ForeignKey` to the :class:`Newsletter` managed by this :class:`NewsletterView`.
	newsletter = models.ForeignKey(Newsletter, related_name='newsletterviews')
	
	#: A :class:`ForeignKey` to the :class:`Page` used to render the main page of this :class:`NewsletterView`.
	index_page = models.ForeignKey(Page, related_name='newsletter_index_related')
	#: A :class:`ForeignKey` to the :class:`Page` used to render the detail view of a :class:`NewsletterArticle` for this :class:`NewsletterView`.
	article_page = models.ForeignKey(Page, related_name='newsletter_article_related')
	#: A :class:`ForeignKey` to the :class:`Page` used to render the :class:`NewsletterArticle` archive pages for this :class:`NewsletterView`.
	article_archive_page = models.ForeignKey(Page, related_name='newsletter_article_archive_related', null=True, blank=True)
	#: A :class:`ForeignKey` to the :class:`Page` used to render the detail view of a :class:`NewsletterIssue` for this :class:`NewsletterView`.
	issue_page = models.ForeignKey(Page, related_name='newsletter_issue_related')
	#: A :class:`ForeignKey` to the :class:`Page` used to render the :class:`NewsletterIssue` archive pages for this :class:`NewsletterView`.
	issue_archive_page = models.ForeignKey(Page, related_name='newsletter_issue_archive_related', null=True, blank=True)
	
	#: Depending on the needs of the site, different permalink styles may be appropriate. Example subpaths are provided for a :class:`NewsletterArticle` posted on May 2nd, 2011 with a slug of "hello". The choices are:
	#: 
	#: 	* Year, month, and day - :attr:`article_permalink_base`\ ``/2011/05/02/hello``
	#: 	* Year and month - :attr:`article_permalink_base`\ ``/2011/05/hello``
	#: 	* Year - :attr:`article_permalink_base`\ ``/2011/hello``
	#: 	* Slug only - :attr:`article_permalink_base`\ ``/hello``
	article_permalink_style = models.CharField(max_length=1, choices=ARTICLE_PERMALINK_STYLE_CHOICES)
	#: This will be used as the base subpath for year/month/day article archive pages and article detail pages. Default: "articles"
	article_permalink_base = models.CharField(max_length=255, blank=False, default='articles')
	#: This will be used as the base subpath for issue detail pages and the issue archive page.
	issue_permalink_base = models.CharField(max_length=255, blank=False, default='issues')
	
	item_context_var = 'articles'
	object_attr = 'newsletter'
	
	def __unicode__(self):
		return "NewsletterView for %s" % self.newsletter.__unicode__()
	
	def get_reverse_params(self, obj):
		if isinstance(obj, NewsletterArticle):
			if obj.newsletter_id == self.newsletter_id:
				kwargs = {'slug': obj.slug}
				if self.article_permalink_style in 'DMY':
					kwargs.update({'year': str(obj.date.year).zfill(4)})
					if self.article_permalink_style in 'DM':
						kwargs.update({'month': str(obj.date.month).zfill(2)})
						if self.article_permalink_style == 'D':
							kwargs.update({'day': str(obj.date.day).zfill(2)})
				return self.article_view, [], kwargs
		elif isinstance(obj, NewsletterIssue):
			if obj.newsletter_id == self.newsletter_id:
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
		if self.issue_archive_page_id:
			urlpatterns += patterns('',
				url(r'^%s$' % self.issue_permalink_base, self.issue_archive_view, 'issue_archive')
			)
		if self.article_archive_page_id:
			urlpatterns += self.feed_patterns(r'^%s' % self.article_permalink_base, 'get_all_articles', 'article_archive_page', 'articles')
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
	
	def get_article_queryset(self, obj):
		"""Returns the default :class:`QuerySet` of :class:`NewsletterArticle` instances for the :class:`NewsletterView` - all articles that are considered posted in the past. This allows for scheduled posting of articles."""
		return obj.articles.filter(date__lte=datetime.now())
	
	def get_issue_queryset(self, obj):
		"""Returns the default :class:`QuerySet` of :class:`NewsletterIssue` instances for the :class:`NewsletterView`."""
		return obj.issues.all()
	
	def get_all_articles(self, obj, request, extra_context=None):
		"""Used to generate :meth:`~.FeedView.feed_patterns` for all entries."""
		return self.get_article_queryset(obj), extra_context
	
	def get_articles_by_ymd(self, obj, request, year, month=None, day=None, extra_context=None):
		"""Used to generate :meth:`~.FeedView.feed_patterns` for a specific year, month, and day."""
		articles = self.get_article_queryset(obj).filter(date__year=year)
		if month:
			articles = articles.filter(date__month=month)
		if day:
			articles = articles.filter(date__day=day)
		return articles, extra_context
	
	def get_articles_by_issue(self, obj, request, numbering, extra_context=None):
		"""Used to generate :meth:`~.FeedView.feed_patterns` for articles from a certain issue."""
		try:
			issue = self.get_issue_queryset(obj).get(numbering=numbering)
		except NewsletterIssue.DoesNotExist:
			raise Http404
		context = extra_context or {}
		context.update({'issue': issue})
		return self.get_article_queryset(obj).filter(issues=issue), context
	
	def article_view(self, request, slug, year=None, month=None, day=None, extra_context=None):
		"""Renders :attr:`article_page` with the article specified by the given parameters."""
		articles = self.get_article_queryset(self.newsletter)
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
		"""Renders :attr:`issue_archive_page` with the result of :meth:`get_issue_queryset` added to the context."""
		if not self.issue_archive_page:
			raise Http404
		context = self.get_context()
		context.update(extra_context or {})
		context.update({
			'issues': self.get_issue_queryset(self.newsletter)
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