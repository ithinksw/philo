from django.http import HttpResponse
from django.utils.decorators import decorator_from_middleware

from philo.contrib.winer.exceptions import HttpNotAcceptable


class HttpNotAcceptableMiddleware(object):
	"""Middleware to catch :exc:`~philo.contrib.winer.exceptions.HttpNotAcceptable` and return an :class:`HttpResponse` with a 406 response code. See :rfc:`2616`."""
	def process_exception(self, request, exception):
		if isinstance(exception, HttpNotAcceptable):
			return HttpResponse(status=406)


http_not_acceptable = decorator_from_middleware(HttpNotAcceptableMiddleware)