from django.core.exceptions import ImproperlyConfigured


#: Raised if ``request.node`` is required but not present. For example, this can be raised by :func:`philo.views.node_view`. :data:`MIDDLEWARE_NOT_CONFIGURED` is an instance of :exc:`django.core.exceptions.ImproperlyConfigured`.
MIDDLEWARE_NOT_CONFIGURED = ImproperlyConfigured("""Philo requires the RequestNode middleware to be installed. Edit your MIDDLEWARE_CLASSES setting to insert 'philo.middleware.RequestNodeMiddleware'.""")


class ViewDoesNotProvideSubpaths(Exception):
	"""Raised by :meth:`.View.reverse` when the :class:`.View` does not provide subpaths (the default)."""
	silent_variable_failure = True


class ViewCanNotProvideSubpath(Exception):
	"""Raised by :meth:`.View.reverse` when the :class:`.View` can not provide a subpath for the supplied arguments."""
	silent_variable_failure = True


class AncestorDoesNotExist(Exception):
	"""Raised by :meth:`.TreeEntity.get_path` if the root instance is not an ancestor of the current instance."""
	pass