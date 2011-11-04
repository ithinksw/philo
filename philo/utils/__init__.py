from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.core.paginator import Paginator, EmptyPage


def fattr(*args, **kwargs):
	"""
	Returns a wrapper which takes a function as its only argument and sets the key/value pairs passed in with kwargs as attributes on that function. This can be used as a decorator.
	
	Example::
	
		>>> from philo.utils import fattr
		>>> @fattr(short_description="Hello World!")
		... def x():
		...     pass
		... 
		>>> x.short_description
		'Hello World!'
	
	"""
	def wrapper(function):
		for key in kwargs:
			setattr(function, key, kwargs[key])
		return function
	return wrapper


### ContentTypeLimiters


class ContentTypeLimiter(object):
	def q_object(self):
		return models.Q(pk__in=[])
	
	def add_to_query(self, query, *args, **kwargs):
		query.add_q(self.q_object(), *args, **kwargs)


class ContentTypeRegistryLimiter(ContentTypeLimiter):
	"""Can be used to limit the choices for a :class:`ForeignKey` or :class:`ManyToManyField` to the :class:`ContentType`\ s which have been registered with this limiter."""
	def __init__(self):
		self.classes = []
	
	def register_class(self, cls):
		"""Registers a model class with this limiter."""
		self.classes.append(cls)
	
	def unregister_class(self, cls):
		"""Unregisters a model class from this limiter."""
		self.classes.remove(cls)
	
	def q_object(self):
		contenttype_pks = []
		for cls in self.classes:
			try:
				if issubclass(cls, models.Model):
					if not cls._meta.abstract:
						contenttype = ContentType.objects.get_for_model(cls)
						contenttype_pks.append(contenttype.pk)
			except:
				pass
		return models.Q(pk__in=contenttype_pks)


class ContentTypeSubclassLimiter(ContentTypeLimiter):
	"""
	Can be used to limit the choices for a :class:`ForeignKey` or :class:`ManyToManyField` to the :class:`ContentType`\ s for all non-abstract models which subclass the class passed in on instantiation.
	
	:param cls: The class whose non-abstract subclasses will be valid choices.
	:param inclusive: Whether ``cls`` should also be considered a valid choice (if it is a non-abstract subclass of :class:`models.Model`)
	
	"""
	def __init__(self, cls, inclusive=False):
		self.cls = cls
		self.inclusive = inclusive
	
	def q_object(self):
		contenttype_pks = []
		def handle_subclasses(cls):
			for subclass in cls.__subclasses__():
				try:
					if issubclass(subclass, models.Model):
						if not subclass._meta.abstract:
							if not self.inclusive and subclass is self.cls:
								continue
							contenttype = ContentType.objects.get_for_model(subclass)
							contenttype_pks.append(contenttype.pk)
					handle_subclasses(subclass)
				except:
					pass
		handle_subclasses(self.cls)
		return models.Q(pk__in=contenttype_pks)


### Pagination


def paginate(objects, per_page=None, page_number=1):
	"""
	Given a list of objects, return a (``paginator``, ``page``, ``objects``) tuple.
	
	:param objects: The list of objects to be paginated.
	:param per_page: The number of objects per page.
	:param page_number: The number of the current page.
	:returns tuple: (``paginator``, ``page``, ``objects``) where ``paginator`` is a :class:`django.core.paginator.Paginator` instance, ``page`` is the result of calling :meth:`Paginator.page` with ``page_number``, and objects is ``page.objects``. Any of the return values which can't be calculated will be returned as ``None``.
	
	"""
	try:
		per_page = int(per_page)
	except (TypeError, ValueError):
		# Then either it wasn't set or it was set to an invalid value
		paginator = page = None
	else:
		# There also shouldn't be pagination if the list is too short. Try count()
		# first - good chance it's a queryset, where count is more efficient.
		try:
			if objects.count() <= per_page:
				paginator = page = None
		except AttributeError:
			if len(objects) <= per_page:
				paginator = page = None
	
	try:
		return paginator, page, objects
	except NameError:
		pass
	
	paginator = Paginator(objects, per_page)
	try:
		page_number = int(page_number)
	except:
		page_number = 1
	
	try:
		page = paginator.page(page_number)
	except EmptyPage:
		page = None
	else:
		objects = page.object_list
	
	return paginator, page, objects