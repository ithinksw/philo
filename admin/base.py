from django.conf import settings
from django.contrib import admin
from django.contrib.contenttypes import generic
from django.http import HttpResponse
from django.utils import simplejson as json
from django.utils.html import escape
from philo.models import Tag, Attribute
from philo.forms import AttributeForm, AttributeInlineFormSet
from philo.admin.widgets import TagFilteredSelectMultiple
from mptt.admin import MPTTModelAdmin


COLLAPSE_CLASSES = ('collapse', 'collapse-closed', 'closed',)


class AttributeInline(generic.GenericTabularInline):
	ct_field = 'entity_content_type'
	ct_fk_field = 'entity_object_id'
	model = Attribute
	extra = 1
	allow_add = True
	classes = COLLAPSE_CLASSES
	form = AttributeForm
	formset = AttributeInlineFormSet
	fields = ['key', 'value_content_type']
	if 'grappelli' in settings.INSTALLED_APPS:
		template = 'admin/philo/edit_inline/grappelli_tabular_attribute.html'
	else:
		template = 'admin/philo/edit_inline/tabular_attribute.html'


class EntityAdmin(admin.ModelAdmin):
	inlines = [AttributeInline]
	save_on_top = True


class TreeAdmin(MPTTModelAdmin):
	pass


class TreeEntityAdmin(TreeAdmin, EntityAdmin):
	pass


class TagAdmin(admin.ModelAdmin):
	list_display = ('name', 'slug')
	prepopulated_fields = {"slug": ("name",)}
	search_fields = ["name"]
	
	def response_add(self, request, obj, post_url_continue='../%s/'):
		# If it's an ajax request, return a json response containing the necessary information.
		if request.is_ajax():
			return HttpResponse(json.dumps({'pk': escape(obj._get_pk_val()), 'unicode': escape(obj)}))
		return super(TagAdmin, self).response_add(request, obj, post_url_continue)


class AddTagAdmin(admin.ModelAdmin):
	def formfield_for_manytomany(self, db_field, request=None, **kwargs):
		"""
		Get a form Field for a ManyToManyField.
		"""
		# If it uses an intermediary model that isn't auto created, don't show
		# a field in admin.
		if not db_field.rel.through._meta.auto_created:
			return None
		
		if db_field.rel.to == Tag and db_field.name in (list(self.filter_vertical) + list(self.filter_horizontal)):
			opts = Tag._meta
			if request.user.has_perm(opts.app_label + '.' + opts.get_add_permission()):
				kwargs['widget'] = TagFilteredSelectMultiple(db_field.verbose_name, (db_field.name in self.filter_vertical))
				return db_field.formfield(**kwargs)
		
		return super(AddTagAdmin, self).formfield_for_manytomany(db_field, request, **kwargs)


admin.site.register(Tag, TagAdmin)