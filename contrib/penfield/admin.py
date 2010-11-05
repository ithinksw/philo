from django.contrib import admin
from philo.admin import EntityAdmin, AddTagAdmin
from philo.contrib.penfield.models import BlogEntry, Blog, BlogView, Newsletter, NewsletterArticle, NewsletterIssue, NewsletterView


class TitledAdmin(EntityAdmin):
	prepopulated_fields = {'slug': ('title',)}
	list_display = ('title', 'slug')


class BlogAdmin(TitledAdmin):
	pass


class BlogEntryAdmin(TitledAdmin, AddTagAdmin):
	filter_horizontal = ['tags']


class BlogViewAdmin(EntityAdmin):
	pass


class NewsletterAdmin(TitledAdmin):
	pass


class NewsletterArticleAdmin(TitledAdmin, AddTagAdmin):
	filter_horizontal = TitledAdmin.filter_horizontal + ('tags', 'authors')


class NewsletterIssueAdmin(TitledAdmin):
	filter_horizontal = TitledAdmin.filter_horizontal + ('articles',)


class NewsletterViewAdmin(EntityAdmin):
	pass


admin.site.register(Blog, BlogAdmin)
admin.site.register(BlogEntry, BlogEntryAdmin)
admin.site.register(BlogView, BlogViewAdmin)
admin.site.register(Newsletter, NewsletterAdmin)
admin.site.register(NewsletterArticle, NewsletterArticleAdmin)
admin.site.register(NewsletterIssue, NewsletterIssueAdmin)
admin.site.register(NewsletterView, NewsletterViewAdmin)