"""
Winer provides the same API as `django's syndication Feed class <http://docs.djangoproject.com/en/dev/ref/contrib/syndication/#django.contrib.syndication.django.contrib.syndication.views.Feed>`_, adapted to a Philo-style :class:`~philo.models.nodes.MultiView` for easy database management. Apps that need syndication can simply subclass :class:`~philo.contrib.winer.models.FeedView`, override a few methods, and start serving RSS and Atom feeds. See :class:`~philo.contrib.penfield.models.BlogView` for a concrete implementation example.

"""