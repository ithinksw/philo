from models import BlogEntry, Blog, BlogView
from django.contrib import admin
from philo.admin import EntityAdmin


class TitledAdmin(EntityAdmin):
	prepopulated_fields = {'slug': ('title',)}
	list_display = ('title', 'slug')


class BlogAdmin(TitledAdmin):
	pass


class BlogEntryAdmin(TitledAdmin):
	pass


class BlogViewAdmin(EntityAdmin):
	pass


admin.site.register(Blog, BlogAdmin)
admin.site.register(BlogEntry, BlogEntryAdmin)
admin.site.register(BlogView, BlogViewAdmin)