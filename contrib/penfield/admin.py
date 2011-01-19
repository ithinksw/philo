from django.contrib import admin
from django import forms
from philo.admin import EntityAdmin, AddTagAdmin, COLLAPSE_CLASSES
from philo.contrib.penfield.models import BlogEntry, Blog, BlogView, Newsletter, NewsletterArticle, NewsletterIssue, NewsletterView


class DelayedDateForm(forms.ModelForm):
	date_field = 'date'
	
	def __init__(self, *args, **kwargs):
		super(DelayedDateForm, self).__init__(*args, **kwargs)
		self.fields[self.date_field].required = False


class TitledAdmin(EntityAdmin):
	prepopulated_fields = {'slug': ('title',)}
	list_display = ('title', 'slug')


class BlogAdmin(TitledAdmin):
	pass


class BlogEntryAdmin(TitledAdmin, AddTagAdmin):
	form = DelayedDateForm
	filter_horizontal = ['tags']
	list_filter = ['author', 'blog']
	date_hierarchy = 'date'
	search_fields = ('content',)
	list_display = ['title', 'date', 'author']
	raw_id_fields = ('author',)
	fieldsets = (
		(None, {
			'fields': ('title', 'author', 'blog')
		}),
		('Content', {
			'fields': ('content', 'excerpt', 'tags'),
		}),
		('Advanced', {
			'fields': ('slug', 'date'),
			'classes': COLLAPSE_CLASSES
		})
	)


class BlogViewAdmin(EntityAdmin):
	fieldsets = (
		(None, {
			'fields': ('blog',)
		}),
		('Pages', {
			'fields': ('index_page', 'entry_page', 'tag_page')
		}),
		('Archive Pages', {
			'fields': ('entry_archive_page', 'tag_archive_page')
		}),
		('Permalinks', {
			'fields': ('entry_permalink_style', 'entry_permalink_base', 'tag_permalink_base'),
			'classes': COLLAPSE_CLASSES
		}),
		('Feeds', {
			'fields': ('feed_suffix', 'feeds_enabled'),
			'classes': COLLAPSE_CLASSES
		})
	)
	raw_id_fields = ('index_page', 'entry_page', 'tag_page', 'entry_archive_page', 'tag_archive_page',)


class NewsletterAdmin(TitledAdmin):
	pass


class NewsletterArticleAdmin(TitledAdmin, AddTagAdmin):
	form = DelayedDateForm
	filter_horizontal = ('tags', 'authors')
	list_filter = ('newsletter',)
	date_hierarchy = 'date'
	search_fields = ('title', 'authors__name',)
	list_display = ['title', 'date', 'author_names']
	fieldsets = (
		(None, {
			'fields': ('title', 'authors', 'newsletter')
		}),
		('Content', {
			'fields': ('full_text', 'lede', 'tags')
		}),
		('Advanced', {
			'fields': ('slug', 'date'),
			'classes': COLLAPSE_CLASSES
		})
	)
	
	def author_names(self, obj):
		return ', '.join([author.get_full_name() for author in obj.authors.all()])
	author_names.short_description = "Authors"


class NewsletterIssueAdmin(TitledAdmin):
	filter_horizontal = TitledAdmin.filter_horizontal + ('articles',)


class NewsletterViewAdmin(EntityAdmin):
	fieldsets = (
		(None, {
			'fields': ('newsletter',)
		}),
		('Pages', {
			'fields': ('index_page', 'article_page', 'issue_page')
		}),
		('Archive Pages', {
			'fields': ('article_archive_page', 'issue_archive_page')
		}),
		('Permalinks', {
			'fields': ('article_permalink_style', 'article_permalink_base', 'issue_permalink_base'),
			'classes': COLLAPSE_CLASSES
		}),
		('Feeds', {
			'fields': ('feed_suffix', 'feeds_enabled'),
			'classes': COLLAPSE_CLASSES
		})
	)
	raw_id_fields = ('index_page', 'article_page', 'issue_page', 'article_archive_page', 'issue_archive_page',)


admin.site.register(Blog, BlogAdmin)
admin.site.register(BlogEntry, BlogEntryAdmin)
admin.site.register(BlogView, BlogViewAdmin)
admin.site.register(Newsletter, NewsletterAdmin)
admin.site.register(NewsletterArticle, NewsletterArticleAdmin)
admin.site.register(NewsletterIssue, NewsletterIssueAdmin)
admin.site.register(NewsletterView, NewsletterViewAdmin)