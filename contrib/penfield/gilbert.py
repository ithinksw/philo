from .models import Blog, BlogEntry, BlogView, NewsletterArticle, NewsletterIssue, Newsletter, NewsletterView
from philo.contrib.gilbert import site


site.register_model(Blog, icon_name='blog')
site.register_model(BlogEntry, search_fields=('title', 'content',), icon_name='document-snippet')
site.register_model(BlogView, icon_name='application-blog')
site.register_model(NewsletterArticle, icon_name='document-snippet')
site.register_model(NewsletterIssue, icon_name='newspaper')
site.register_model(Newsletter, icon_name='newspapers')
site.register_model(NewsletterView, icon_name='application')