from models import BlogEntry, Blog, BlogNode
from django.contrib import admin
from philo.admin import EntityAdmin


class TitledAdmin(EntityAdmin):
	prepopulated_fields = {'slug': ('title',)}
	list_display = ('title', 'slug')


class BlogAdmin(TitledAdmin):
	pass


class BlogEntryAdmin(TitledAdmin):
	pass


class BlogNodeAdmin(EntityAdmin):
	pass


admin.site.register(Blog, BlogAdmin)
admin.site.register(BlogEntry, BlogEntryAdmin)
admin.site.register(BlogNode, BlogNodeAdmin)