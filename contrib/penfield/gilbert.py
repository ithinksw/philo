from .models import Blog, BlogEntry, BlogView, NewsletterArticle, NewsletterIssue, Newsletter, NewsletterView
from philo.contrib.gilbert import site
from philo.contrib.gilbert.plugins.models import ModelAdmin


class BlogAdmin(ModelAdmin):
	search_fields = ('title',)


class BlogEntryAdmin(ModelAdmin):
	search_fields = ('title', 'content',)
	data_columns = ('title', 'author', 'blog', 'date',)


site.register_model(Blog, BlogAdmin, icon_name='blog')
site.register_model(BlogEntry, BlogEntryAdmin, icon_name='document-snippet')
site.register_model(BlogView, icon_name='application-blog')
site.register_model(NewsletterArticle, icon_name='document-snippet')
site.register_model(NewsletterIssue, icon_name='newspaper')
site.register_model(Newsletter, icon_name='newspapers')
site.register_model(NewsletterView, icon_name='application')