from django.core.exceptions import ImproperlyConfigured


MIDDLEWARE_NOT_CONFIGURED = ImproperlyConfigured("""Philo requires the RequestNode middleware to be installed. Edit your MIDDLEWARE_CLASSES setting to insert 'philo.middleware.RequestNodeMiddleware'.""")


class ViewDoesNotProvideSubpaths(Exception):
	""" Raised by get_subpath when the View does not provide subpaths (the default). """
	silent_variable_failure = True


class ViewCanNotProvideSubpath(Exception):
	""" Raised by get_subpath when the View can not provide a subpath for the supplied object. """
	silent_variable_failure = True


class AncestorDoesNotExist(Exception):
	""" Raised by get_path if the root model is not an ancestor of the current model """
	pass