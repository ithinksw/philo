from models import BlogEntry, Blog
from django.contrib import admin
from philo.admin import EntityAdmin

class TitledContentAdmin(EntityAdmin):
	prepopulated_fields = {'slug': ('title',)}
	list_display = ('title', 'slug')


admin.site.register(BlogEntry, TitledContentAdmin)
admin.site.register(Blog)