from django.conf.urls.defaults import url, include, patterns, handler404, handler500
from philo.views import node_view


urlpatterns = patterns('',
	url(r'^$', node_view, name='philo-root'),
	url(r'^(?P<path>.*)$', node_view, name='philo-node-by-path')
)
