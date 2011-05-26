How to get started with philo
=============================

After installing `philo`_ and `mptt`_ on your python path, make sure to complete the following steps:

1. add :mod:`philo` and :mod:`mptt` to :setting:`settings.INSTALLED_APPS`::
	
	INSTALLED_APPS = (
		...
		'philo',
		'mptt',
		...
	)
	
2. add :class:`philo.middleware.RequestNodeMiddleware` to :setting:`settings.MIDDLEWARE_CLASSES`::
	
	MIDDLEWARE_CLASSES = (
		...
		'philo.middleware.RequestNodeMiddleware',
		...
	)
	
3. include :mod:`philo.urls` somewhere in your urls.py file. For example::
	
	from django.conf.urls.defaults import patterns, include, url
	urlpatterns = patterns('',
		url(r'^', include('philo.urls')),
	)
	
4. Optionally add a root :class:`node <philo.models.Node>` to your current :class:`Site` in the admin interface.

Philo should be ready to go!

.. _philo: http://philocms.org/
.. _mptt: http://github.com/django-mptt/django-mptt
