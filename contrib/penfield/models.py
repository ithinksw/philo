from django.db import models
from django.conf import settings
from philo.models import Tag, Titled, Entity, MultiView, Page, register_value_model
from philo.exceptions import ViewCanNotProvideSubpath
from django.conf.urls.defaults import url, patterns, include
from django.core.urlresolvers import reverse
from django.http import Http404, HttpResponse
from datetime import datetime
from philo.utils import paginate
from philo.contrib.penfield.validators import validate_pagination_count
from django.utils.feedgenerator import Atom1Feed, Rss201rev2Feed


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


register_value_model(BlogEntry)


class BlogView(MultiView):
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
	feed_suffix = models.CharField(max_length=255, blank=False, default='feed')
	feeds_enabled = models.BooleanField() 
	
	def __unicode__(self):
		return u'BlogView for %s' % self.blog.title
	
	@property
	def _feeds_enabled(self):
		return self.feeds_enabled
	
	@property
	def per_page(self):
		return self.entries_per_page
	
	def get_subpath(self, obj):
		if isinstance(obj, BlogEntry):
			if obj.blog == self.blog:
				entry_view_args = {'slug': obj.slug}
				if self.entry_permalink_style in 'DMY':
					entry_view_args.update({'year': str(obj.date.year).zfill(4)})
					if self.entry_permalink_style in 'DM':
						entry_view_args.update({'month': str(obj.date.month).zfill(2)})
						if self.entry_permalink_style == 'D':
							entry_view_args.update({'day': str(obj.date.day).zfill(2)})
				return reverse(self.entry_view, urlconf=self, kwargs=entry_view_args)
		elif isinstance(obj, Tag):
			if obj in self.blog.entry_tags:
				return reverse(self.tag_view, urlconf=self, kwargs={'tag_slugs': obj.slug})
		elif isinstance(obj, (str, unicode)):
			split_obj = obj.split(':')
			if len(split_obj) > 1:
				entry_archive_view_args = {}
				if split_obj[0].lower() == 'archives':
					entry_archive_view_args.update({'year': str(int(split_obj[1])).zfill(4)})
					if len(split_obj) > 2:
						entry_archive_view_args.update({'month': str(int(split_obj[2])).zfill(2)})
						if len(split_obj) > 3:
							entry_archive_view_args.update({'day': str(int(split_obj[3])).zfill(2)})
					return reverse(self.entry_archive_view, urlconf=self, kwargs=entry_archive_view_args)
		raise ViewCanNotProvideSubpath

	def page_view(self, func, page, list_var='entries'):
		"""
		Wraps an object-fetching function and renders the results as a page.
		"""
		def inner(request, node=None, extra_context=None, **kwargs):
			objects, extra_context = func(request, node, extra_context, **kwargs)

			context = self.get_context()
			context.update(extra_context or {})

			if 'page' in kwargs or 'page' in request.GET:
				page_num = kwargs.get('page', request.GET.get('page', 1))
				paginator, paginated_page, objects = paginate(objects, self.per_page, page_num)
				context.update({'paginator': paginator, 'paginated_page': paginated_page, list_var: objects})
			else:
				context.update({list_var: objects})

			return page.render_to_response(node, request, extra_context=context)

		return inner

	def get_atom_feed(self):
		return Atom1Feed(self.blog.title, '/%s/%s/' % (node.get_absolute_url().strip('/'), reverse(reverse_name, urlconf=self, kwargs=kwargs).strip('/')), '', subtitle='')
	
	def get_rss_feed(self):
		return Rss201rev2Feed(self.blog.title, '/%s/%s/' % (node.get_absolute_url().strip('/'), reverse(reverse_name, urlconf=self, kwargs=kwargs).strip('/')), '')

	def feed_view(self, func, reverse_name):
		"""
		Wraps an object-fetching function and renders the results as a rss or atom feed.
		"""
		def inner(request, node=None, extra_context=None, **kwargs):
			objects, extra_context = func(request, node, extra_context, **kwargs)
			
			if 'HTTP_ACCEPT' in request.META and 'rss' in request.META['HTTP_ACCEPT'] and 'atom' not in request.META['HTTP_ACCEPT']:
				feed = self.get_rss_feed()
			else:
				feed = self.get_atom_feed()
			
			for obj in objects:
				feed.add_item(obj.title, '/%s/%s/' % (node.get_absolute_url().strip('/'), self.get_subpath(obj).strip('/')), description=obj.excerpt)
			
			response = HttpResponse(mimetype=feed.mime_type)
			feed.write(response, 'utf-8')
			return response
		
		return inner
	
	def get_context(self):
		return {'blog': self.blog}
	
	def feed_patterns(self, object_fetcher, page, base_name):
		feed_name = '%s_feed' % base_name
		urlpatterns = patterns('',
			url(r'^%s/$' % self.feed_suffix, self.feed_view(object_fetcher, feed_name), name=feed_name),
			url(r'^$', self.page_view(object_fetcher, page), name=base_name)
		)
		return urlpatterns
	
	@property
	def urlpatterns(self):
		base_patterns = patterns('',
			url(r'^', include(self.feed_patterns(self.get_all_entries, self.index_page, 'index'))),
			url((r'^(?:%s)/?$' % self.tag_permalink_base), self.tag_archive_view),
			url((r'^(?:%s)/(?P<tag_slugs>[-\w]+[-+/\w]*)/' % self.tag_permalink_base), include(self.feed_patterns(self.get_entries_by_tag, self.tag_page, 'entries_by_tag')))
		)
		if self.entry_permalink_style == 'D':
			entry_patterns = patterns('',
				url(r'^(?P<year>\d{4})/', include(self.feed_patterns(self.get_entries_by_ymd, self.entry_archive_page, 'entries_by_year'))),
				url(r'^(?P<year>\d{4})/(?P<month>\d{2})/?$', include(self.feed_patterns(self.get_entries_by_ymd, self.entry_archive_page, 'entries_by_month'))),
				url(r'^(?P<year>\d{4})/(?P<month>\d{2})/(?P<day>\d{2})/?$', include(self.feed_patterns(self.get_entries_by_ymd, self.entry_archive_page, 'entries_by_day'))),
				url(r'^(?P<year>\d{4})/(?P<month>\d{2})/(?P<day>\d{2})/(?P<slug>[-\w]+)/?$', self.entry_view)
			)
		elif self.entry_permalink_style == 'M':
			entry_patterns = patterns('',
				url(r'^(?P<year>\d{4})/', include(self.feed_patterns(self.get_entries_by_ymd, self.entry_archive_page, 'entries_by_year'))),
				url(r'^(?P<year>\d{4})/(?P<month>\d{2})/?$', include(self.feed_patterns(self.get_entries_by_ymd, self.entry_archive_page, 'entries_by_month'))),
				url(r'^(?P<year>\d{4})/(?P<month>\d{2})/(?P<slug>[-\w]+)/?$', self.entry_view)
			)
		elif self.entry_permalink_style == 'Y':
			entry_patterns = patterns('',
				url(r'^(?P<year>\d{4})/', include(self.feed_patterns(self.get_entries_by_ymd, self.entry_archive_page, 'entries_by_year'))),
				url(r'^(?P<year>\d{4})/(?P<slug>[-\w]+)/?$', self.entry_view)
			)
		elif self.entry_permalink_style == 'B':
			entry_patterns = patterns('',
				url((r'^(?:%s)/?$' % self.entry_permalink_base), 
					url(r'^(?P<year>\d{4})/', include(self.feed_patterns(self.get_all_entries, self.entry_archive_page, 'entries_by_year'))),),
				url((r'^(?:%s)/(?P<slug>[-\w]+)/?$' % self.entry_permalink_base), self.entry_view)
			)
		else:
			entry_patterns = patterns('',
				url(r'^(?P<slug>[-\w]+)/?$', self.entry_view)
			)
		return base_patterns + entry_patterns
	
	def get_all_entries(self, request, node=None, extra_context=None):
		return self.blog.entries.all(), extra_context
	
	def get_entries_by_ymd(self, request, year=None, month=None, day=None, node=None, extra_context=None):
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
	
	def get_entries_by_tag(self, request, node=None, extra_context=None):
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
		if entries.count() <= 0:
			raise Http404
		
		return entries, extra_context
	
	def entry_view(self, request, slug, year=None, month=None, day=None, node=None, extra_context=None):
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
		return self.entry_page.render_to_response(node, request, extra_context=context)
	
	def tag_archive_view(self, request, node=None, extra_context=None):
		if not self.tag_archive_page:
			raise Http404
		context = {}
		context.update(extra_context or {})
		context.update({'blog': self.blog})
		return self.tag_archive_page.render_to_response(node, request, extra_context=context)


class Newsletter(Entity, Titled):
	pass


register_value_model(Newsletter)


class NewsletterArticle(Entity, Titled):
	newsletter = models.ForeignKey(Newsletter, related_name='articles')
	authors = models.ManyToManyField(getattr(settings, 'PHILO_PERSON_MODULE', 'auth.User'), related_name='newsletterarticles')
	date = models.DateTimeField(default=datetime.now)
	lede = models.TextField(null=True, blank=True)
	full_text = models.TextField()
	
	class Meta:
		get_latest_by = 'date'
		ordering = ['-date']
		unique_together = (('newsletter', 'slug'),)


register_value_model(NewsletterArticle)


class NewsletterIssue(Entity, Titled):
	newsletter = models.ForeignKey(Newsletter, related_name='issues')
	number = models.PositiveIntegerField()
	articles = models.ManyToManyField(NewsletterArticle, related_name='issues')
	
	class Meta:
		ordering = ['-number']
		unique_together = (('newsletter', 'number'),)


register_value_model(NewsletterIssue)


class NewsletterView(MultiView):
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
	
	def get_subpath(self, obj):
		if isinstance(obj, NewsletterArticle):
			if obj.newsletter == self.newsletter:
				article_view_args = {'slug': obj.slug}
				if self.article_permalink_style in 'DMY':
					article_view_args.update({'year': str(obj.date.year).zfill(4)})
					if self.article_permalink_style in 'DM':
						article_view_args.update({'month': str(obj.date.month).zfill(2)})
						if self.article_permalink_style == 'D':
							article_view_args.update({'day': str(obj.date.day).zfill(2)})
				return reverse(self.article_view, urlconf=self, kwargs=article_view_args)
		elif isinstance(obj, NewsletterIssue):
			if obj.newsletter == self.newsletter:
				return reverse(self.issue_view, urlconf=self, kwargs={'number': str(obj.number)})
		raise ViewCanNotProvideSubpath
	
	@property
	def urlpatterns(self):
		base_patterns = patterns('',
			url(r'^$', self.index_view),
			url((r'^(?:%s)/?$' % self.issue_permalink_base), self.issue_archive_view),
			url((r'^(?:%s)/(?P<number>\d+)/?$' % self.issue_permalink_base), self.issue_view)
		)
		article_patterns = patterns('',
			url((r'^(?:%s)/?$' % self.article_permalink_base), self.article_archive_view)
		)
		if self.article_permalink_style in 'DMY':
			article_patterns += patterns('',
				url((r'^(?:%s)/(?P<year>\d{4})/?$' % self.article_permalink_base), self.article_archive_view)
			)
			if self.article_permalink_style in 'DM':
				article_patterns += patterns('',
					url((r'^(?:%s)/(?P<year>\d{4})/(?P<month>\d{2})/?$' % self.article_permalink_base), self.article_archive_view)
				)
				if self.article_permalink_style == 'D':
					article_patterns += patterns('',
						url((r'^(?:%s)/(?P<year>\d{4})/(?P<month>\d{2})/(?P<day>\d{2})/?$' % self.article_permalink_base), self.article_archive_view),
						url((r'^(?:%s)/(?P<year>\d{4})/(?P<month>\d{2})/(?P<day>\d{2})/(?P<slug>[-\w]+)/?$' % self.article_permalink_base), self.article_view)
					)
				else:
					article_patterns += patterns('',
						url((r'^(?:%s)/(?P<year>\d{4})/(?P<month>\d{2})/(?P<slug>[-\w]+)/?$' % self.article_permalink_base), self.article_view)
					)
			else:
				article_patterns += patterns('',
					url((r'^(?:%s)/(?P<year>\d{4})/(?P<slug>[-\w]+)/?$' % self.article_permalink_base), self.article_view)
				)
		else:
			article_patterns += patterns('',
				url((r'^(?:%s)/(?P<slug>[-\w]+)/?$' % self.article_permalink_base), self.article_view)
			)
		return base_patterns + article_patterns
	
	def index_view(self, request, node=None, extra_context=None):
		context = {}
		context.update(extra_context or {})
		context.update({'newsletter': self.newsletter})
		return self.index_page.render_to_response(node, request, extra_context=context)
	
	def article_view(self, request, slug, year=None, month=None, day=None, node=None, extra_context=None):
		articles = self.newsletter.articles.all()
		if year:
			articles = articles.filter(date__year=year)
		if month:
			articles = articles.filter(date__month=month)
		if day:
			articles = articles.filter(date__day=day)
		try:
			article = articles.get(slug=slug)
		except:
			raise Http404
		context = {}
		context.update(extra_context or {})
		context.update({'newsletter': self.newsletter, 'article': article})
		return self.article_page.render_to_response(node, request, extra_context=context)
	
	def article_archive_view(self, request, year=None, month=None, day=None, node=None, extra_context=None):
		if not self.article_archive_page:
			raise Http404
		articles = self.newsletter.articles.all()
		if year:
			articles = articles.filter(date__year=year)
		if month:
			articles = articles.filter(date__month=month)
		if day:
			articles = articles.filter(date__day=day)
		context = {}
		context.update(extra_context or {})
		context.update({'newsletter': self.newsletter, 'year': year, 'month': month, 'day': day, 'articles': articles})
		return self.article_archive_page.render_to_response(node, request, extra_context=context)
	
	def issue_view(self, request, number, node=None, extra_context=None):
		try:
			issue = self.newsletter.issues.get(number=number)
		except:
			raise Http404
		context = {}
		context.update(extra_context or {})
		context.update({'newsletter': self.newsletter, 'issue': issue})
		return self.issue_page.render_to_response(node, request, extra_context=context)
	
	def issue_archive_view(self, request, node=None, extra_context=None):
		if not self.issue_archive_page:
			raise Http404
		context = {}
		context.update(extra_context or {})
		context.update({'newsletter': self.newsletter})
		return self.issue_archive_page.render_to_response(node, request, extra_context=context)