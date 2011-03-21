from django.http import HttpResponse
from django.utils.decorators import decorator_from_middleware
from philo.contrib.penfield.exceptions import HttpNotAcceptable


class HttpNotAcceptableMiddleware(object):
	"""Middleware to catch HttpNotAcceptable errors and return an Http406 response.
	See RFC 2616."""
	def process_exception(self, request, exception):
		if isinstance(exception, HttpNotAcceptable):
			return HttpResponse(status=406)


http_not_acceptable = decorator_from_middleware(HttpNotAcceptableMiddleware)