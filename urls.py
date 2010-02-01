from django.conf.urls.defaults import url, include, patterns, handler404, handler500
from philo.views import page_view


urlpatterns = patterns('',
	url(r'^$', page_view, name='philo-root'),
	url(r'^(?P<path>.*)$', page_view, name='philo-page-by-path')
)
