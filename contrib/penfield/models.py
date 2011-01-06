from django.db import models
from django.conf import settings
from philo.models import Tag, Titled, Entity, MultiView, Page, register_value_model, TemplateField
from philo.exceptions import ViewCanNotProvideSubpath
from django.conf.urls.defaults import url, patterns, include
from django.http import Http404
from datetime import date, datetime
from philo.utils import paginate
from philo.contrib.penfield.validators import validate_pagination_count
from django.utils.feedgenerator import Atom1Feed, Rss201rev2Feed
from philo.contrib.penfield.utils import FeedMultiViewMixin


class Blog(Entity, Titled):
	@property
	def entry_tags(self):
		""" Returns a QuerySet of Tags that are used on any entries in this blog. """
		return Tag.objects.filter(blogentries__blog=self).distinct()
	
	@property
	def entry_dates(self):
		dates = {'year': self.entries.dates('date', 'year', order='DESC'), 'month': self.entries.dates('date', 'month', order='DESC'), 'day': self.entries.dates('date', 'day', order='DESC')}
		return dates


register_value_model(Blog)


class BlogEntry(Entity, Titled):
	blog = models.ForeignKey(Blog, related_name='entries', blank=True, null=True)
	author = models.ForeignKey(getattr(settings, 'PHILO_PERSON_MODULE', 'auth.User'), related_name='blogentries')
	date = models.DateTimeField(default=datetime.now)
	content = models.TextField()
	excerpt = models.TextField(blank=True, null=True)
	tags = models.ManyToManyField(Tag, related_name='blogentries', blank=True, null=True)
	
	class Meta:
		ordering = ['-date']
		verbose_name_plural = "blog entries"
		get_latest_by = "date"


register_value_model(BlogEntry)


class BlogView(MultiView, FeedMultiViewMixin):
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
	entry_archive_page = models.ForeignKey(Page, related_name='blog_entry_archive_related', null=True, blank=True)
	tag_page = models.ForeignKey(Page, related_name='blog_tag_related')
	tag_archive_page = models.ForeignKey(Page, related_name='blog_tag_archive_related', null=True, blank=True)
	entries_per_page = models.IntegerField(blank=True, validators=[validate_pagination_count], null=True)
	
	entry_permalink_style = models.CharField(max_length=1, choices=ENTRY_PERMALINK_STYLE_CHOICES)
	entry_permalink_base = models.CharField(max_length=255, blank=False, default='entries')
	tag_permalink_base = models.CharField(max_length=255, blank=False, default='tags')
	feed_suffix = models.CharField(max_length=255, blank=False, default=FeedMultiViewMixin.feed_suffix)
	feeds_enabled = models.BooleanField()
	list_var = 'entries'
	
	def __unicode__(self):
		return u'BlogView for %s' % self.blog.title
	
	@property
	def per_page(self):
		return self.entries_per_page
	
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
		elif isinstance(obj, Tag):
			if obj in self.blog.entry_tags:
				return 'entries_by_tag', [], {'tag_slugs': obj.slug}
		elif isinstance(obj, (date, datetime)):
			kwargs = {
				'year': str(obj.year).zfill(4),
				'month': str(obj.month).zfill(2),
				'day': str(obj.day).zfill(2)
			}
			return 'entries_by_day', [], kwargs
		raise ViewCanNotProvideSubpath
	
	def get_context(self):
		return {'blog': self.blog}
	
	@property
	def urlpatterns(self):
		urlpatterns = patterns('',
			url(r'^', include(self.feed_patterns(self.get_all_entries, self.index_page, 'index'))),
		)
		if self.feeds_enabled:
			urlpatterns += patterns('',
				url(r'^%s/(?P<tag_slugs>[-\w]+[-+/\w]*)/%s/' % (self.tag_permalink_base, self.feed_suffix), self.feed_view(self.get_entries_by_tag, 'entries_by_tag_feed'), name='entries_by_tag_feed'),
			)
		urlpatterns += patterns('',
			url(r'^%s/(?P<tag_slugs>[-\w]+[-+/\w]*)/' % self.tag_permalink_base, self.page_view(self.get_entries_by_tag, self.tag_page), name='entries_by_tag')
		)
		if self.tag_archive_page:
			urlpatterns += patterns('',
				url((r'^(?:%s)/?$' % self.tag_permalink_base), self.tag_archive_view)
			)
		
		if self.entry_archive_page:
			if self.entry_permalink_style in 'DMY':
				urlpatterns += patterns('',
					url(r'^(?P<year>\d{4})/', include(self.feed_patterns(self.get_entries_by_ymd, self.entry_archive_page, 'entries_by_year')))
				)
				if self.entry_permalink_style in 'DM':
					urlpatterns += patterns('',
						url(r'^(?P<year>\d{4})/(?P<month>\d{2})/?$', include(self.feed_patterns(self.get_entries_by_ymd, self.entry_archive_page, 'entries_by_month'))),
					)
					if self.entry_permalink_style == 'D':
						urlpatterns += patterns('',
							url(r'^(?P<year>\d{4})/(?P<month>\d{2})/(?P<day>\d{2})/?$', include(self.feed_patterns(self.get_entries_by_ymd, self.entry_archive_page, 'entries_by_day')))
						)
		
		if self.entry_permalink_style == 'D':
			urlpatterns += patterns('',
				url(r'^(?P<year>\d{4})/(?P<month>\d{2})/(?P<day>\d{2})/(?P<slug>[-\w]+)/?$', self.entry_view)
			)
		elif self.entry_permalink_style == 'M':
			urlpatterns += patterns('',
				url(r'^(?P<year>\d{4})/(?P<month>\d{2})/(?P<slug>[-\w]+)/?$', self.entry_view)
			)
		elif self.entry_permalink_style == 'Y':
			urlpatterns += patterns('',
				url(r'^(?P<year>\d{4})/(?P<slug>[-\w]+)/?$', self.entry_view)
			)
		elif self.entry_permalink_style == 'B':
			urlpatterns += patterns('',
				url((r'^(?:%s)/(?P<slug>[-\w]+)/?$' % self.entry_permalink_base), self.entry_view)
			)
		else:
			urlpatterns = patterns('',
				url(r'^(?P<slug>[-\w]+)/?$', self.entry_view)
			)
		return urlpatterns
	
	def get_all_entries(self, request, extra_context=None):
		return self.blog.entries.all(), extra_context
	
	def get_entries_by_ymd(self, request, year=None, month=None, day=None, extra_context=None):
		if not self.entry_archive_page:
			raise Http404
		entries = self.blog.entries.all()
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
		tags = []
		for tag_slug in tag_slugs.replace('+', '/').split('/'):
			if tag_slug: # ignore blank slugs, handles for multiple consecutive separators (+ or /)
				try:
					tag = self.blog.entry_tags.get(slug=tag_slug)
				except:
					raise Http404
				tags.append(tag)
		if len(tags) <= 0:
			raise Http404

		entries = self.blog.entries.all()
		for tag in tags:
			entries = entries.filter(tags=tag)
		
		context = self.get_context()
		context.update(extra_context or {})
		context.update({'tags': tags})
		
		return entries, context
	
	def add_item(self, feed, obj, kwargs=None):
		defaults = {
			'title': obj.title,
			'description': obj.content,
			'author_name': obj.author.get_full_name(),
			'pubdate': obj.date
		}
		defaults.update(kwargs or {})
		super(BlogView, self).add_item(feed, obj, defaults)
	
	def get_feed(self, feed_type, extra_context, kwargs=None):
		tags = (extra_context or {}).get('tags', None)
		title = self.blog.title
		
		if tags is not None:
			title += " - %s" % ', '.join([tag.name for tag in tags])
		
		defaults = {
			'title': title
		}
		defaults.update(kwargs or {})
		return super(BlogView, self).get_feed(feed_type, extra_context, defaults)
	
	def entry_view(self, request, slug, year=None, month=None, day=None, extra_context=None):
		entries = self.blog.entries.all()
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
		context = {}
		context.update(extra_context or {})
		context.update({'blog': self.blog})
		return self.tag_archive_page.render_to_response(request, extra_context=context)


class Newsletter(Entity, Titled):
	pass


register_value_model(Newsletter)


class NewsletterArticle(Entity, Titled):
	newsletter = models.ForeignKey(Newsletter, related_name='articles')
	authors = models.ManyToManyField(getattr(settings, 'PHILO_PERSON_MODULE', 'auth.User'), related_name='newsletterarticles')
	date = models.DateTimeField(default=datetime.now)
	lede = TemplateField(null=True, blank=True, verbose_name='Summary')
	full_text = TemplateField(db_index=True)
	tags = models.ManyToManyField(Tag, related_name='newsletterarticles', blank=True, null=True)
	
	class Meta:
		get_latest_by = 'date'
		ordering = ['-date']
		unique_together = (('newsletter', 'slug'),)


register_value_model(NewsletterArticle)


class NewsletterIssue(Entity, Titled):
	newsletter = models.ForeignKey(Newsletter, related_name='issues')
	numbering = models.CharField(max_length=50, help_text='For example, 04.02 for volume 4, issue 2.')
	articles = models.ManyToManyField(NewsletterArticle, related_name='issues')
	
	class Meta:
		ordering = ['-numbering']
		unique_together = (('newsletter', 'numbering'),)


register_value_model(NewsletterIssue)


class NewsletterView(MultiView, FeedMultiViewMixin):
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
	
	feed_suffix = models.CharField(max_length=255, blank=False, default=FeedMultiViewMixin.feed_suffix)
	feeds_enabled = models.BooleanField()
	list_var = 'articles'
	
	def __unicode__(self):
		return self.newsletter.__unicode__()
	
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
		urlpatterns = patterns('',
			url(r'^', include(self.feed_patterns(self.get_all_articles, self.index_page, 'index'))),
			url(r'^(?:%s)/(?P<numbering>.+)/' % self.issue_permalink_base, include(self.feed_patterns(self.get_articles_by_issue, self.issue_page, 'issue')))
		)
		if self.issue_archive_page:
			urlpatterns += patterns('',
				url(r'^(?:%s)/$' % self.issue_permalink_base, self.issue_archive_view)
			)
		if self.article_archive_page:
			urlpatterns += patterns('',
				url(r'^(?:%s)/' % self.article_permalink_base, include(self.feed_patterns(self.get_all_articles, self.article_archive_page, 'articles')))
			)
			if self.article_permalink_style in 'DMY':
				urlpatterns += patterns('',
					url(r'^(?:%s)/(?P<year>\d{4})/' % self.article_permalink_base, include(self.feed_patterns(self.get_articles_by_ymd, self.article_archive_page, 'articles_by_year')))
				)
				if self.article_permalink_style in 'DM':
					urlpatterns += patterns('',
						url(r'^(?:%s)/(?P<year>\d{4})/(?P<month>\d{2})/' % self.article_permalink_base, include(self.feed_patterns(self.get_articles_by_ymd, self.article_archive_page, 'articles_by_month')))
					)
					if self.article_permalink_style == 'D':
						urlpatterns += patterns('',
							url(r'^(?:%s)/(?P<year>\d{4})/(?P<month>\d{2})/(?P<day>\d{2})/' % self.article_permalink_base, include(self.feed_patterns(self.get_articles_by_ymd, self.article_archive_page, 'articles_by_day')))
						)
		
		if self.article_permalink_style == 'Y':
			urlpatterns += patterns('',
				url(r'^(?:%s)/(?P<year>\d{4})/(?P<slug>[\w-]+)/$' % self.article_permalink_base, self.article_view)
			)
		elif self.article_permalink_style == 'M':
			urlpatterns += patterns('',
				url(r'^(?:%s)/(?P<year>\d{4})/(?P<month>\d{2})/(?P<slug>[\w-]+)/$' % self.article_permalink_base, self.article_view)
			)
		elif self.article_permalink_style == 'D':
			urlpatterns += patterns('',
				url(r'^(?:%s)/(?P<year>\d{4})/(?P<month>\d{2})/(?P<day>\d{2})/(?P<slug>[\w-]+)/$' % self.article_permalink_base, self.article_view)
			)
		else:	
			urlpatterns += patterns('',
				url(r'^(?:%s)/(?P<slug>[-\w]+)/?$' % self.article_permalink_base, self.article_view)
			)
		
		return urlpatterns
	
	def get_context(self):
		return {'newsletter': self.newsletter}
	
	def get_all_articles(self, request, extra_context=None):
		return self.newsletter.articles.all(), extra_context
	
	def get_articles_by_ymd(self, request, year, month=None, day=None, extra_context=None):
		articles = self.newsletter.articles.filter(dat__year=year)
		if month:
			articles = articles.filter(date__month=month)
		if day:
			articles = articles.filter(date__day=day)
		return articles
	
	def get_articles_by_issue(self, request, numbering, extra_context=None):
		try:
			issue = self.newsletter.issues.get(numbering=numbering)
		except NewsletterIssue.DoesNotExist:
			raise Http404
		context = extra_context or {}
		context.update({'issue': issue})
		return issue.articles.all(), context
	
	def article_view(self, request, slug, year=None, month=None, day=None, extra_context=None):
		articles = self.newsletter.articles.all()
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
	
	def issue_archive_view(self, request, extra_context=None):
		if not self.issue_archive_page:
			raise Http404
		context = {}
		context.update(extra_context or {})
		context.update({'newsletter': self.newsletter})
		return self.issue_archive_page.render_to_response(request, extra_context=context)
	
	def add_item(self, feed, obj, kwargs=None):
		defaults = {
			'title': obj.title,
			'author_name': ', '.join([author.get_full_name() for author in obj.authors.all()]),
			'pubdate': obj.date,
			'description': obj.full_text,
			'categories': [tag.name for tag in obj.tags.all()]
		}
		defaults.update(kwargs or {})
		super(NewsletterView, self).add_item(feed, obj, defaults)
	
	def get_feed(self, feed_type, extra_context, kwargs=None):
		title = self.newsletter.title
		
		defaults = {
			'title': title
		}
		defaults.update(kwargs or {})
		return super(NewsletterView, self).get_feed(feed_type, extra_context, defaults)
