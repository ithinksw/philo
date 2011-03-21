class AlreadyRegistered(Exception):
	pass


class NotRegistered(Exception):
	pass


class ExtException(Exception):
	""" Base class for all Ext.Direct-related exceptions. """
	pass


class InvalidExtMethod(ExtException):
	""" Indicate that a function cannot be an Ext.Direct method. """
	pass


class NotExtAction(ExtException):
	""" Indicate that an object is not an Ext.Direct action. """
	pass


class NotExtMethod(ExtException):
	""" Indicate that a function is not an Ext.Direct method. """
	pass