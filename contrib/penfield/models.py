from django.db import models
from philo.models import Entity, Collection, MultiNode, Template, register_value_model
from django.contrib.auth.models import User
from django.conf.urls.defaults import url, patterns
from django.http import Http404, HttpResponse


class Entry(Entity):
	author = models.ForeignKey(User, related_name='blogpost_author')
	pub_date = models.DateTimeField(auto_now_add=True)
	mod_date = models.DateTimeField(auto_now=True)
	title = models.CharField(max_length=255)
	slug = models.SlugField()
	content = models.TextField()
	excerpt = models.TextField()


register_value_model(Entry)


class Blog(MultiNode):
	PERMALINK_STYLE_CHOICES = (
		('D', 'Year, month, and day'),
		('M', 'Year and month'),
		('Y', 'Year'),
		('B', 'Custom base'),
		('N', 'No base')
	)
	
	posts = models.ForeignKey(Collection, related_name='blogs')
	index_template = models.ForeignKey(Template, related_name='blog_index_related')
	archive_template = models.ForeignKey(Template, related_name='blog_archive_related')
	tag_template = models.ForeignKey(Template, related_name='blog_tag_related')
	post_template = models.ForeignKey(Template, related_name='blog_post_related')
	
	post_permalink_style = models.CharField(max_length=1, choices=PERMALINK_STYLE_CHOICES)
	post_permalink_base = models.CharField(max_length=255, blank=False, default='posts')
	tag_permalink_base = models.CharField(max_length=255, blank=False, default='tags')
	
	@property
	def post_queryset(self):
		# this won't be ordered according to the collection member indexes
		return self.posts.members.with_model(Entry)
	
	@property
	def urlpatterns(self):
		base_patterns = patterns('',
			url(r'^$', self.index_view),
			url((r'^(?:%s)/?' % self.tag_permalink_base), self.tag_view),
			url((r'^(?:%s)/(?P<tag>\w+)/?' % self.tag_permalink_base), self.tag_view)
		)
		if self.post_permalink_style == 'D':
			post_patterns = patterns('',
				url(r'^(?P<year>\d{4})/?$', self.archive_view),
				url(r'^(?P<year>\d{4})/(?P<month>\d{2})/?$', self.archive_view),
				url(r'^(?P<year>\d{4})/(?P<month>\d{2})/(?P<day>\d+)/?$', self.archive_view),
				url(r'^(?P<year>\d{4})/(?P<month>\d{2})/(?P<day>\d+)/(?P<slug>\w+)/?', self.archive_view)
			)
		elif self.post_permalink_style == 'M':
			post_patterns = patterns('',
				url(r'^(?P<year>\d{4})/?$', self.archive_view),
				url(r'^(?P<year>\d{4})/(?P<month>\d{2})/?$', self.archive_view),
				url(r'^(?P<year>\d{4})/(?P<month>\d{2})/(?P<slug>\w+)/?', self.archive_view)
			)
		elif self.post_permalink_style == 'Y':
			post_patterns = patterns('',
				url(r'^(?P<year>\d{4})/?$', self.archive_view),
				url(r'^(?P<year>\d{4})/(?P<slug>\w+)/?', self.post_view)
			)
		elif self.post_permalink_style == 'B':
			post_patterns = patterns('',
				url((r'^(?:%s)/?' % self.post_permalink_base), self.archive_view),
				url((r'^(?:%s)/(?P<slug>\w+)/?' % self.post_permalink_base), self.post_view)
			)
		else:
			post_patterns = patterns('',
				url(r'^(?P<slug>\w+)/?', self.post_view)
			)
		return base_patterns + post_patterns
	
	def index_view(self, request):
		raise Http404
	
	def archive_view(self, request, year=None, month=None, day=None):
		raise Http404
	
	def tag_view(self, request, tag=None):
		raise Http404
	
	def post_view(self, request, year=None, month=None, day=None, slug=None):
		raise Http404
