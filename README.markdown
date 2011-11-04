[Philo](http://philocms.org/) is a foundation for developing web content management systems.

Prerequisites:

 * [Python 2.5.4+](http://www.python.org/)
 * [Django 1.3+](http://www.djangoproject.com/)
 * [django-mptt e734079+](https://github.com/django-mptt/django-mptt/)
 * (optional) [django-grappelli 2.0+](http://code.google.com/p/django-grappelli/)
 * (optional) [south 0.7.2+](http://south.aeracode.org/)
 * (philo.contrib.penfield) [django-taggit 0.9.3+](https://github.com/alex/django-taggit/)
 * (philo.contrib.waldo, optional) [recaptcha-django r6+](http://code.google.com/p/recaptcha-django/)

After installing philo and mptt on your PYTHONPATH, make sure to complete the following steps:

1. Add 'philo.middleware.RequestNodeMiddleware' to settings.MIDDLEWARE_CLASSES.
2. Add 'philo' and 'mptt' to settings.INSTALLED_APPS.
3. Include 'philo.urls' somewhere in your urls.py file.
4. Optionally add a root node to your current Site.
5. (philo.contrib.gilbert) Add 'django.core.context_processors.request' to settings.TEMPLATE_CONTEXT_PROCESSORS.

Philo should be ready to go! All that's left is to [learn more](http://docs.philocms.org/) and [contribute](http://docs.philocms.org/en/latest/contribute.html).
