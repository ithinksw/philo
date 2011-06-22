from django.core.validators import slug_re
from django.template.defaultfilters import slugify
from django.utils.encoding import smart_str


class RegistryIterator(object):
	"""
	Wraps the iterator returned by calling ``getattr(registry, iterattr)`` to provide late instantiation of the wrapped iterator and to allow copying of the iterator for even later instantiation.
	
	:param registry: The object which provides the iterator at ``iterattr``.
	:param iterattr: The name of the method on ``registry`` that provides the iterator.
	:param transform: A function which will be called on each result from the wrapped iterator before it is returned.
	
	"""
	def __init__(self, registry, iterattr='__iter__', transform=lambda x:x):
		if not hasattr(registry, iterattr):
			raise AttributeError("Registry has no attribute %s" % iterattr)
		self.registry = registry
		self.iterattr = iterattr
		self.transform = transform
	
	def __iter__(self):
		return self
	
	def next(self):
		if not hasattr(self, '_iter'):
			self._iter = getattr(self.registry, self.iterattr)()
		
		return self.transform(self._iter.next())
	
	def copy(self):
		"""Returns a fresh copy of this iterator."""
		return self.__class__(self.registry, self.iterattr, self.transform)


class RegistrationError(Exception):
	"""Raised if there is a problem registering a object with a :class:`Registry`"""
	pass


class Registry(object):
	"""Holds a registry of arbitrary objects by slug."""
	
	def __init__(self):
		self._registry = {}
	
	def register(self, obj, slug=None, verbose_name=None):
		"""
		Register an object with the registry.
		
		:param obj: The object to register.
		:param slug: The slug which will be used to register the object. If ``slug`` is ``None``, it will be generated from ``verbose_name`` or looked for at ``obj.slug``.
		:param verbose_name: The verbose name for the object. If ``verbose_name`` is ``None``, it will be looked for at ``obj.verbose_name``.
		:raises: :class:`RegistrationError` if a different object is already registered with ``slug``, or if ``slug`` is not a valid slug.
		
		"""
		verbose_name = verbose_name if verbose_name is not None else obj.verbose_name
		
		if slug is None:
			slug = getattr(obj, 'slug', slugify(verbose_name))
		slug = smart_str(slug)
		
		if not slug_re.search(slug):
			raise RegistrationError(u"%s is not a valid slug." % slug)
		
		
		if slug in self._registry:
			reg = self._registry[slug]
			if reg['obj'] != obj:
				raise RegistrationError(u"A different object is already registered as `%s`" % slug)
		else:
			self._registry[slug] = {
				'obj': obj,
				'verbose_name': verbose_name
			}
	
	def unregister(self, obj, slug=None):
		"""
		Unregister an object from the registry.
		
		:param obj: The object to unregister.
		:param slug: If provided, the object will only be removed if it was registered with ``slug``. If not provided, the object will be unregistered no matter what slug it was registered with.
		:raises: :class:`RegistrationError` if ``slug`` is provided and an object other than ``obj`` is registered as ``slug``.
		
		"""
		if slug is not None:
			if slug in self._registry:
				if self._registry[slug]['obj'] == obj:
					del self._registry[slug]
				else:
					raise RegistrationError(u"`%s` is not registered as `%s`" % (obj, slug))
		else:
			for slug, reg in self.items():
				if obj == reg:
					del self._registry[slug]
	
	def items(self):
		"""Returns a list of (slug, obj) items in the registry."""
		return [(slug, self[slug]) for slug in self._registry]
	
	def values(self):
		"""Returns a list of objects in the registry."""
		return [self[slug] for slug in self._registry]
	
	def iteritems(self):
		"""Returns a :class:`RegistryIterator` over the (slug, obj) pairs in the registry."""
		return RegistryIterator(self._registry, 'iteritems', lambda x: (x[0], x[1]['obj']))
	
	def itervalues(self):
		"""Returns a :class:`RegistryIterator` over the objects in the registry."""
		return RegistryIterator(self._registry, 'itervalues', lambda x: x['obj'])
	
	def iterchoices(self):
		"""Returns a :class:`RegistryIterator` over (slug, verbose_name) pairs for the registry."""
		return RegistryIterator(self._registry, 'iteritems', lambda x: (x[0], x[1]['verbose_name']))
	choices = property(iterchoices)
	
	def get(self, key, default=None):
		"""Returns the object registered with ``key`` or ``default`` if no object was registered."""
		try:
			return self[key]
		except KeyError:
			return default
	
	def get_slug(self, obj, default=None):
		"""Returns the slug used to register ``obj`` or ``default`` if ``obj`` was not registered."""
		for slug, reg in self.iteritems():
			if obj == reg:
				return slug
		return default
	
	def __getitem__(self, key):
		"""Returns the obj registered with ``key``."""
		return self._registry[key]['obj']
	
	def __iter__(self):
		"""Returns an iterator over the keys in the registry."""
		return self._registry.__iter__()
	
	def __contains__(self, item):
		return self._registry.__contains__(item)