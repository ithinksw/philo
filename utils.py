from django.db import models
from django.contrib.contenttypes.models import ContentType


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
