from inspect import isclass, getargspec


def is_gilbert_method(function):
	return getattr(function, 'gilbert_method', False)


def gilbert_method(function=None, name=None, argc=None, restricted=True):
	def wrapper(function):
		setattr(function, 'gilbert_method', True)
		setattr(function, 'name', name or function.__name__)
		setattr(function, 'restricted', restricted)
		new_argc = argc
		if new_argc is None:
			args = getargspec(function)[0]
			new_argc = len(args)
			if new_argc > 0:
				if args[0] == 'self':
					args = args[1:]
					new_argc = new_argc - 1
				if new_argc > 0:
					if args[0] == 'request':
						args = args[1:]
						new_argc = new_argc - 1
		setattr(function, 'argc', new_argc)
		return function
	if function is not None:
		return wrapper(function)
	return wrapper


class GilbertPluginBase(type):
	def __new__(cls, name, bases, attrs):
		if 'methods' not in attrs:
			methods = []
			for attr in attrs.values():
				if is_gilbert_method(attr):
					methods.append(attr.name)
			attrs['methods'] = methods
		return super(GilbertPluginBase, cls).__new__(cls, name, bases, attrs)


class GilbertPlugin(object):
	__metaclass__ = GilbertPluginBase
	
	def __init__(self, site):
		self.site = site
	
	def get_method(self, method_name):
		method = getattr(self, method_name, None)
		if not is_gilbert_method(method):
			return None
		return method
	
	@property
	def urls(self):
		return []
	
	@property
	def js(self):
		return []
	
	@property
	def css(self):
		return []
	
	@property
	def fugue_icons(self):
		return []


class GilbertModelAdmin(GilbertPlugin):
	def __init__(self, site, model):
		self.model = model
		self.name = model._meta.object_name
		super(GilbertModelAdmin, self).__init__(site)
	
	@gilbert_method
	def all(self):
		return list(self.model._default_manager.all().values())
	
	@gilbert_method
	def get(self, constraint):
		return self.model._default_manager.all().values().get(**constraint)