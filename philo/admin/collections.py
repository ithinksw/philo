from django.contrib import admin

from philo.admin.base import COLLAPSE_CLASSES
from philo.models import CollectionMember, Collection


class CollectionMemberInline(admin.TabularInline):
	fk_name = 'collection'
	model = CollectionMember
	extra = 1
	classes = COLLAPSE_CLASSES
	allow_add = True
	fields = ('member_content_type', 'member_object_id', 'index')
	sortable_field_name = 'index'


class CollectionAdmin(admin.ModelAdmin):
	inlines = [CollectionMemberInline]
	list_display = ('name', 'description', 'get_count')


admin.site.register(Collection, CollectionAdmin)