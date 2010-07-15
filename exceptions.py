class ViewDoesNotProvideSubpaths(Exception):
	""" Raised by get_subpath when the View does not provide subpaths (the default). """
	silent_variable_failure = True

class ViewCanNotProvideSubpath(Exception):
	""" Raised by get_subpath when the View can not provide a subpath for the supplied object. """
	silent_variable_failure = True