from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.core.paginator import Paginator, EmptyPage
from django.template import Context
from django.template.loader_tags import ExtendsNode, ConstantIncludeNode


class ContentTypeLimiter(object):
	def q_object(self):
		return models.Q(pk__in=[])
	
	def add_to_query(self, query, *args, **kwargs):
		query.add_q(self.q_object(), *args, **kwargs)


class ContentTypeRegistryLimiter(ContentTypeLimiter):
	def __init__(self):
		self.classes = []
	
	def register_class(self, cls):
		self.classes.append(cls)
	
	def unregister_class(self, cls):
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


def fattr(*args, **kwargs):
	def wrapper(function):
		for key in kwargs:
			setattr(function, key, kwargs[key])
		return function
	return wrapper


def paginate(objects, per_page=None, page_number=1):
	"""
	Given a list of objects, return a (paginator, page, objects) tuple.
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


LOADED_TEMPLATE_ATTR = '_philo_loaded_template'
BLANK_CONTEXT = Context()


def get_extended(self):
	return self.get_parent(BLANK_CONTEXT)


def get_included(self):
	return self.template


# We ignore the IncludeNode because it will never work in a blank context.
setattr(ExtendsNode, LOADED_TEMPLATE_ATTR, property(get_extended))
setattr(ConstantIncludeNode, LOADED_TEMPLATE_ATTR, property(get_included))