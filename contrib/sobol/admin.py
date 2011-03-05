from django.conf import settings
from django.conf.urls.defaults import patterns, url
from django.contrib import admin
from django.core.urlresolvers import reverse
from django.db.models import Count
from django.http import HttpResponseRedirect, Http404
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.utils.functional import update_wrapper
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
		results_template = 'admin/sobol/search/grappelli_results.html'
	else:
		results_template = 'admin/sobol/search/results.html'
	
	def get_urls(self):
		urlpatterns = super(SearchAdmin, self).get_urls()
		
		def wrap(view):
			def wrapper(*args, **kwargs):
				return self.admin_site.admin_view(view)(*args, **kwargs)
			return update_wrapper(wrapper, view)
		
		info = self.model._meta.app_label, self.model._meta.module_name
		
		urlpatterns = patterns('',
			url(r'^results/$', wrap(self.results_view), name="%s_%s_selected_results" % info),
			url(r'^(.+)/results/$', wrap(self.results_view), name="%s_%s_results" % info)
		) + urlpatterns
		return urlpatterns
	
	def unique_urls(self, obj):
		return obj.unique_urls
	unique_urls.admin_order_field = 'unique_urls'
	
	def total_clicks(self, obj):
		return obj.total_clicks
	total_clicks.admin_order_field = 'total_clicks'
	
	def queryset(self, request):
		qs = super(SearchAdmin, self).queryset(request)
		return qs.annotate(total_clicks=Count('result_urls__clicks', distinct=True), unique_urls=Count('result_urls', distinct=True))
	
	def results_action(self, request, queryset):
		info = self.model._meta.app_label, self.model._meta.module_name
		if len(queryset) == 1:
			return HttpResponseRedirect(reverse("admin:%s_%s_results" % info, args=(queryset[0].pk,)))
		else:
			url = reverse("admin:%s_%s_selected_results" % info)
			return HttpResponseRedirect("%s?ids=%s" % (url, ','.join([str(item.pk) for item in queryset])))
	results_action.short_description = "View results for selected %(verbose_name_plural)s"
	
	def results_view(self, request, object_id=None, extra_context=None):
		if object_id is not None:
			object_ids = [object_id]
		else:
			object_ids = request.GET.get('ids').split(',')
			
			if object_ids is None:
				raise Http404
		
		qs = self.queryset(request).filter(pk__in=object_ids)
		opts = self.model._meta
		
		if len(object_ids) == 1:
			title = _(u"Search results for %s" % qs[0])
		else:
			title = _(u"Search results for multiple objects")
		
		context = {
			'title': title,
			'queryset': qs,
			'opts': opts,
			'root_path': self.admin_site.root_path,
			'app_label': opts.app_label
		}
		return render_to_response(self.results_template, context, context_instance=RequestContext(request))


class SearchViewAdmin(EntityAdmin):
	raw_id_fields = ('results_page',)
	related_lookup_fields = {'fk': raw_id_fields}


admin.site.register(Search, SearchAdmin)
admin.site.register(SearchView, SearchViewAdmin)