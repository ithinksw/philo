from django.db import models
from philo.models import Entity, MultiNode, Template, register_value_model
from django.contrib.auth.models import User
from django.conf.urls.defaults import url, patterns
from django.http import Http404, HttpResponse
from django.template import RequestContext
from datetime import datetime
from utils import paginate
from validators import validate_pagination_count


class Tag(models.Model):
	name = models.CharField(max_length=250)
	slug = models.SlugField()
	
	def __unicode__(self):
		return self.name


class Titled(models.Model):
	title = models.CharField(max_length=255)
	slug = models.SlugField()
	
	def __unicode__(self):
		return self.title
	
	class Meta:
		abstract = True


class Blog(Entity, Titled):
	pass


class BlogEntry(Entity, Titled):
	blog = models.ForeignKey(Blog, related_name='entries')
	author = models.ForeignKey(User, related_name='blogentries')
	date = models.DateTimeField(default=datetime.now)
	content = models.TextField()
	excerpt = models.TextField()
	tags = models.ManyToManyField(Tag)
	
	class Meta:
		ordering = ['-date']
		verbose_name_plural = "Blog Entries"


register_value_model(BlogEntry)


class BlogNode(MultiNode):
	PERMALINK_STYLE_CHOICES = (
		('D', 'Year, month, and day'),
		('M', 'Year and month'),
		('Y', 'Year'),
		('B', 'Custom base'),
		('N', 'No base')
	)
	
	blog = models.ForeignKey(Blog, related_name='nodes')
	
	index_template = models.ForeignKey(Template, related_name='blog_index_related')
	archive_template = models.ForeignKey(Template, related_name='blog_archive_related')
	tag_template = models.ForeignKey(Template, related_name='blog_tag_related')
	entries_per_page = models.IntegerField(blank=True, validators=[validate_pagination_count])
	entry_template = models.ForeignKey(Template, related_name='blog_entry_related')
	
	entry_permalink_style = models.CharField(max_length=1, choices=PERMALINK_STYLE_CHOICES)
	entry_permalink_base = models.CharField(max_length=255, blank=False, default='entries')
	tag_permalink_base = models.CharField(max_length=255, blank=False, default='tags')
	
	@property
	def urlpatterns(self):
		base_patterns = patterns('',
			url(r'^$', self.index_view),
			url((r'^(?:%s)/?' % self.tag_permalink_base), self.tag_view),
			url((r'^(?:%s)/(?P<tag>>[-\w]+)/?' % self.tag_permalink_base), self.tag_view)
		)
		if self.entry_permalink_style == 'D':
			entry_patterns = patterns('',
				url(r'^(?P<year>\d{4})/?$', self.archive_view),
				url(r'^(?P<year>\d{4})/(?P<month>\d{2})/?$', self.archive_view),
				url(r'^(?P<year>\d{4})/(?P<month>\d{2})/(?P<day>\d+)/?$', self.archive_view),
				url(r'^(?P<year>\d{4})/(?P<month>\d{2})/(?P<day>\d+)/(?P<slug>[-\w]+)/?', self.entry_view)
			)
		elif self.entry_permalink_style == 'M':
			entry_patterns = patterns('',
				url(r'^(?P<year>\d{4})/?$', self.archive_view),
				url(r'^(?P<year>\d{4})/(?P<month>\d{2})/?$', self.archive_view),
				url(r'^(?P<year>\d{4})/(?P<month>\d{2})/(?P<slug>>[-\w]+)/?', self.entry_view)
			)
		elif self.entry_permalink_style == 'Y':
			entry_patterns = patterns('',
				url(r'^(?P<year>\d{4})/?$', self.archive_view),
				url(r'^(?P<year>\d{4})/(?P<slug>>[-\w]+)/?', self.entry_view)
			)
		elif self.entry_permalink_style == 'B':
			entry_patterns = patterns('',
				url((r'^(?:%s)/?' % self.entry_permalink_base), self.archive_view),
				url((r'^(?:%s)/(?P<slug>>[-\w]+)/?' % self.entry_permalink_base), self.entry_view)
			)
		else:
			entry_patterns = patterns('',
				url(r'^(?P<slug>>[-\w]+)/?', self.entry_view)
			)
		return base_patterns + entry_patterns
	
	def index_view(self, request):
		entries = self.blog.entries.order_by('-date')
		if self.entries_per_page:
			page = paginate(request, entries, self.entries_per_page)
			entries = page.object_list
		else:
			page = None
		return HttpResponse(self.index_template.django_template.render(RequestContext(request, {'blog': self.blog, 'entries': entries, 'page': page})), mimetype=self.index_template.mimetype)
	
	def archive_view(self, request, year=None, month=None, day=None):
		entries = self.blog.entries.all()
		if year:
			entries = entries.filter(date__year=year)
		if month:
			entries = entries.filter(date__month=month)
		if day:
			entries = entries.filter(date__day=day)
		if self.entries_per_page:
			page = paginate(request, entries, self.entries_per_page)
			entries = page.object_list
		else:
			page = None
		return HttpResponse(self.archive_template.django_template.render(RequestContext(request, {'blog': self.blog, 'year': year, 'month': month, 'day': day, 'entries': entries, 'page': page})), mimetype=self.archive_template.mimetype)
	
	def tag_view(self, request, tag=None):
		entries = self.blog.entries.filter(tags__slug = tag)
		if self.entries_per_page:
			page = paginate(request, entries, self.entries_per_page)
			entries = page.object_list
		else:
			page = None
		return HttpResponse(self.tag_template.django_template.render(RequestContext(request, {'blog': self.blog, 'tag': tag, 'entries': entries, 'page': page})), mimetype=self.tag_template.mimetype)
		raise Http404
	
	def entry_view(self, request, slug, year=None, month=None, day=None):
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
		return HttpResponse(self.entry_template.django_template.render(RequestContext(request, {'blog': self.blog, 'entry': entry})), mimetype=self.entry_template.mimetype)


class Newsletter(Entity, Titled):
	pass


class NewsStory(Entity, Titled):
	newsletter = models.ForeignKey(Newsletter, related_name='stories')
	authors = models.ManyToManyField(User, related_name='newsstories')
	date = models.DateTimeField(default=datetime.now)
	lede = models.TextField(null=True, blank=True)
	full_text = models.TextField()


register_value_model(NewsStory)