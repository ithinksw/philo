from django.contrib import admin
from django.contrib.contenttypes import generic
from philo.models import Tag, Attribute
from philo.forms import AttributeForm, AttributeInlineFormSet


COLLAPSE_CLASSES = ('collapse', 'collapse-closed', 'closed',)


class AttributeInline(generic.GenericTabularInline):
	ct_field = 'entity_content_type'
	ct_fk_field = 'entity_object_id'
	model = Attribute
	extra = 1
	template = 'admin/philo/edit_inline/tabular_attribute.html'
	allow_add = True
	classes = COLLAPSE_CLASSES
	form = AttributeForm
	formset = AttributeInlineFormSet
	exclude = ['value_object_id']


class EntityAdmin(admin.ModelAdmin):
	inlines = [AttributeInline]
	save_on_top = True


class TagAdmin(admin.ModelAdmin):
	list_display = ('name', 'slug')
	prepopulated_fields = {"slug": ("name",)}
	search_fields = ["name"]

admin.site.register(Tag, TagAdmin)