from django.contrib import admin
#from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic
#from django import forms
#from django.conf import settings
#from django.utils.translation import ugettext as _
#from django.utils.safestring import mark_safe
#from django.utils.html import escape
#from django.utils.text import truncate_words
from philo.models import *
#from philo.admin import widgets
#from django.core.exceptions import ValidationError, ObjectDoesNotExist
#from validators import TreeParentValidator, TreePositionValidator


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