try:
	from django.utils.functional import empty, LazyObject, SimpleLazyObject
except ImportError:
	# Supply LazyObject and SimpleLazyObject for django < r16308
	import operator
	
	
	empty = object()
	def new_method_proxy(func):
		def inner(self, *args):
			if self._wrapped is empty:
				self._setup()
			return func(self._wrapped, *args)
		return inner

	class LazyObject(object):
		"""
		A wrapper for another class that can be used to delay instantiation of the
		wrapped class.

		By subclassing, you have the opportunity to intercept and alter the
		instantiation. If you don't need to do that, use SimpleLazyObject.
		"""
		def __init__(self):
			self._wrapped = empty

		__getattr__ = new_method_proxy(getattr)

		def __setattr__(self, name, value):
			if name == "_wrapped":
				# Assign to __dict__ to avoid infinite __setattr__ loops.
				self.__dict__["_wrapped"] = value
			else:
				if self._wrapped is empty:
					self._setup()
				setattr(self._wrapped, name, value)

		def __delattr__(self, name):
			if name == "_wrapped":
				raise TypeError("can't delete _wrapped.")
			if self._wrapped is empty:
				self._setup()
			delattr(self._wrapped, name)

		def _setup(self):
			"""
			Must be implemented by subclasses to initialise the wrapped object.
			"""
			raise NotImplementedError

		# introspection support:
		__members__ = property(lambda self: self.__dir__())
		__dir__ = new_method_proxy(dir)


	class SimpleLazyObject(LazyObject):
		"""
		A lazy object initialised from any function.

		Designed for compound objects of unknown type. For builtins or objects of
		known type, use django.utils.functional.lazy.
		"""
		def __init__(self, func):
			"""
			Pass in a callable that returns the object to be wrapped.

			If copies are made of the resulting SimpleLazyObject, which can happen
			in various circumstances within Django, then you must ensure that the
			callable can be safely run more than once and will return the same
			value.
			"""
			self.__dict__['_setupfunc'] = func
			super(SimpleLazyObject, self).__init__()

		def _setup(self):
			self._wrapped = self._setupfunc()

		__str__ = new_method_proxy(str)
		__unicode__ = new_method_proxy(unicode)

		def __deepcopy__(self, memo):
			if self._wrapped is empty:
				# We have to use SimpleLazyObject, not self.__class__, because the
				# latter is proxied.
				result = SimpleLazyObject(self._setupfunc)
				memo[id(self)] = result
				return result
			else:
				import copy
				return copy.deepcopy(self._wrapped, memo)

		# Need to pretend to be the wrapped class, for the sake of objects that care
		# about this (especially in equality tests)
		__class__ = property(new_method_proxy(operator.attrgetter("__class__")))
		__eq__ = new_method_proxy(operator.eq)
		__hash__ = new_method_proxy(hash)
		__nonzero__ = new_method_proxy(bool)