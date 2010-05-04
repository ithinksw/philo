from models import Entry, Blog
from django.contrib import admin
from philo.admin import EntityAdmin

admin.site.register(Entry, EntityAdmin)
admin.site.register(Blog)