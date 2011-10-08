from django import forms
from django.contrib import admin
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect, QueryDict

from philo.admin import EntityAdmin, COLLAPSE_CLASSES
from philo.admin.widgets import EmbedWidget
from philo.contrib.penfield.models import BlogEntry, Blog, BlogView, Newsletter, NewsletterArticle, NewsletterIssue, NewsletterView
from philo.models.fields import TemplateField


class DelayedDateForm(forms.ModelForm):
	date_field = 'date'
	
	def __init__(self, *args, **kwargs):
		super(DelayedDateForm, self).__init__(*args, **kwargs)
		self.fields[self.date_field].required = False


class BlogAdmin(EntityAdmin):
	prepopulated_fields = {'slug': ('title',)}
	list_display = ('title', 'slug')


class BlogEntryAdmin(EntityAdmin):
	form = DelayedDateForm
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
	related_lookup_fields = {'fk': raw_id_fields}
	prepopulated_fields = {'slug': ('title',)}
	formfield_overrides = {
		TemplateField: {'widget': EmbedWidget}
	}


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
		('General Settings', {
			'fields': ('entry_permalink_style', 'entry_permalink_base', 'tag_permalink_base', 'entries_per_page'),
			'classes': COLLAPSE_CLASSES
		}),
		('Feed Settings', {
			'fields': ( 'feeds_enabled', 'feed_suffix', 'feed_type', 'feed_length', 'item_title_template', 'item_description_template',),
			'classes': COLLAPSE_CLASSES
		})
	)
	raw_id_fields = ('index_page', 'entry_page', 'tag_page', 'entry_archive_page', 'tag_archive_page', 'item_title_template', 'item_description_template',)
	related_lookup_fields = {'fk': raw_id_fields}


class NewsletterAdmin(EntityAdmin):
	prepopulated_fields = {'slug': ('title',)}
	list_display = ('title', 'slug')


class NewsletterArticleAdmin(EntityAdmin):
	form = DelayedDateForm
	filter_horizontal = ('authors',)
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
	actions = ['make_issue']
	prepopulated_fields = {'slug': ('title',)}
	formfield_overrides = {
		TemplateField: {'widget': EmbedWidget}
	}
	
	def author_names(self, obj):
		return ', '.join([author.get_full_name() for author in obj.authors.all()])
	author_names.short_description = "Authors"
	
	def make_issue(self, request, queryset):
		opts = NewsletterIssue._meta
		info = opts.app_label, opts.module_name
		url = reverse("admin:%s_%s_add" % info)
		return HttpResponseRedirect("%s?articles=%s" % (url, ",".join([str(a.pk) for a in queryset])))
	make_issue.short_description = u"Create issue from selected %(verbose_name_plural)s"


class NewsletterIssueAdmin(EntityAdmin):
	filter_horizontal = ('articles',)
	prepopulated_fields = {'slug': ('title',)}
	list_display = ('title', 'slug')


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
			'fields': ( 'feeds_enabled', 'feed_suffix', 'feed_type', 'feed_length', 'item_title_template', 'item_description_template',),
			'classes': COLLAPSE_CLASSES
		})
	)
	raw_id_fields = ('index_page', 'article_page', 'issue_page', 'article_archive_page', 'issue_archive_page', 'item_title_template', 'item_description_template',)
	related_lookup_fields = {'fk': raw_id_fields}


admin.site.register(Blog, BlogAdmin)
admin.site.register(BlogEntry, BlogEntryAdmin)
admin.site.register(BlogView, BlogViewAdmin)
admin.site.register(Newsletter, NewsletterAdmin)
admin.site.register(NewsletterArticle, NewsletterArticleAdmin)
admin.site.register(NewsletterIssue, NewsletterIssueAdmin)
admin.site.register(NewsletterView, NewsletterViewAdmin)