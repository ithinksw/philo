from django.contrib import admin
from django.db.models import Count
from philo.admin import EntityAdmin
from philo.contrib.sobol.models import Search, ResultURL, SearchView


class ResultURLInline(admin.TabularInline):
	model = ResultURL
	template = 'search/admin/chosen_result_inline.html'
	readonly_fields = ('url',)
	can_delete = False
	extra = 0
	max_num = 0


class SearchAdmin(admin.ModelAdmin):
	readonly_fields = ('string',)
	inlines = [ResultURLInline]
	list_display = ['string', 'unique_urls', 'total_clicks']
	search_fields = ['string', 'result_urls__url']
	
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