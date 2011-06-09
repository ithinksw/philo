class Category(type):
	"""
	Adds attributes to an existing class.
	
	"""
	
	replace_attrs = False
	dunder_attrs = False
	never_attrs = ('__module__', '__metaclass__')
	
	def __new__(cls, name, bases, attrs):
		if len(bases) != 1:
			raise AttributeError('%s: "%s" cannot add methods to more than one class.' % (cls.__name__, name))
		
		base = bases[0]
		
		for attr, value in attrs.iteritems():
			if attr in cls.never_attrs:
				continue
			if not cls.dunder_attrs and attr.startswith('__'):
				continue
			if not cls.replace_attrs and hasattr(base, attr):
				continue
			setattr(base, attr, value)
		
		return base


class MonkeyPatch(type):
	"""
	Similar to Category, except it will replace attributes.
	
	"""
	
	replace_attrs = True
	dunder_attrs = Category.dunder_attrs
	never_attrs = Category.never_attrs
	
	unpatches = {}
	
	@classmethod
	def unpatched(cls, klass, name):
		try:
			return cls.unpatches[klass][name]
		except:
			return getattr(klass, name)
	
	def __new__(cls, name, bases, attrs):
		if len(bases) != 1:
			raise AttributeError('%s: "%s" cannot patch more than one class.' % (cls.__name__, name))
		
		base = bases[0]
		
		for attr, value in attrs.iteritems():
			if attr in cls.never_attrs:
				continue
			if not cls.dunder_attrs and attr.startswith('__'):
				continue
			if hasattr(base, attr):
				if not cls.replace_attrs:
					continue
				else:
					if base not in cls.unpatches:
						cls.unpatches[base] = {}
					cls.unpatches[base][attr] = getattr(base, attr)
			
			setattr(base, attr, value)
		
		return base