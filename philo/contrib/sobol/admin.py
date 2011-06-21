from functools import update_wrapper

from django.conf import settings
from django.conf.urls.defaults import patterns, url
from django.contrib import admin
from django.core.urlresolvers import reverse
from django.db.models import Count
from django.http import HttpResponseRedirect, Http404
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.utils.translation import ugettext_lazy as _

from philo.admin import EntityAdmin
from philo.contrib.sobol.models import Search, ResultURL, SearchView


class ResultURLInline(admin.TabularInline):
	model = ResultURL
	readonly_fields = ('url',)
	can_delete = False
	extra = 0
	max_num = 0


class SearchAdmin(admin.ModelAdmin):
	readonly_fields = ('string',)
	inlines = [ResultURLInline]
	list_display = ['string', 'unique_urls', 'total_clicks']
	search_fields = ['string', 'result_urls__url']
	actions = ['results_action']
	if 'grappelli' in settings.INSTALLED_APPS:
		change_form_template = 'admin/sobol/search/grappelli_change_form.html'
	
	def unique_urls(self, obj):
		return obj.unique_urls
	unique_urls.admin_order_field = 'unique_urls'
	
	def total_clicks(self, obj):
		return obj.total_clicks
	total_clicks.admin_order_field = 'total_clicks'
	
	def queryset(self, request):
		qs = super(SearchAdmin, self).queryset(request)
		return qs.annotate(total_clicks=Count('result_urls__clicks', distinct=True), unique_urls=Count('result_urls', distinct=True))


class SearchViewAdmin(EntityAdmin):
	raw_id_fields = ('results_page',)
	related_lookup_fields = {'fk': raw_id_fields}


admin.site.register(Search, SearchAdmin)
admin.site.register(SearchView, SearchViewAdmin)