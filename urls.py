from django.conf.urls.defaults import patterns, url
from philo.views import node_view


urlpatterns = patterns('',
	url(r'^$', node_view, name='philo-root'),
	url(r'^(?P<path>.*)$', node_view, name='philo-node-by-path')
)
