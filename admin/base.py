from django.contrib import admin
from django.contrib.contenttypes import generic
from philo.models import Tag, Attribute, Relationship


COLLAPSE_CLASSES = ('collapse', 'collapse-closed', 'closed',)


class AttributeInline(generic.GenericTabularInline):
	ct_field = 'entity_content_type'
	ct_fk_field = 'entity_object_id'
	model = Attribute
	extra = 1
	template = 'admin/philo/edit_inline/tabular_collapse.html'
	allow_add = True


class RelationshipInline(generic.GenericTabularInline):
	ct_field = 'entity_content_type'
	ct_fk_field = 'entity_object_id'
	model = Relationship
	extra = 1
	template = 'admin/philo/edit_inline/tabular_collapse.html'
	allow_add = True


class EntityAdmin(admin.ModelAdmin):
	inlines = [AttributeInline, RelationshipInline]
	save_on_top = True


admin.site.register(Tag)