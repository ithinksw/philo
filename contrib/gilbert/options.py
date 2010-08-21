from philo.contrib.gilbert.utils import gilbert_method, is_gilbert_method, is_gilbert_class


class GilbertClassBase(type):
	def __new__(cls, name, bases, attrs):
		if 'gilbert_class' not in attrs:
			attrs['gilbert_class'] = True
		if 'gilbert_class_name' not in attrs:
			attrs['gilbert_class_name'] = name
		if 'gilbert_class_methods' not in attrs:
			gilbert_class_methods = {}
			for attr in attrs.values():
				if is_gilbert_method(attr):
					gilbert_class_methods[attr.gilbert_method_name] = attr
			attrs['gilbert_class_methods'] = gilbert_class_methods
		return super(GilbertClassBase, cls).__new__(cls, name, bases, attrs)


class GilbertClass(object):
	__metaclass__ = GilbertClassBase


class GilbertPluginBase(type):
	def __new__(cls, name, bases, attrs):
		if 'gilbert_plugin' not in attrs:
			attrs['gilbert_plugin'] = True
		if 'gilbert_plugin_name' not in attrs:
			attrs['gilbert_plugin_name'] = name
		if 'gilbert_plugin_classes' not in attrs:
			gilbert_plugin_classes = {}
			for attr_name, attr in attrs.items():
				if is_gilbert_class(attr):
					gilbert_plugin_classes[attr_name] = attr
			attrs['gilbert_plugin_classes'] = gilbert_plugin_classes
		return super(GilbertPluginBase, cls).__new__(cls, name, bases, attrs)


class GilbertPlugin(object):
	__metaclass__ = GilbertPluginBase
	
	def __init__(self, site):
		self.site = site


class GilbertModelAdmin(GilbertClass):
	def __init__(self, site, model):
		self.site = site
		self.model = model
		self.gilbert_class_name = model._meta.object_name
	
	@gilbert_method
	def all(self):
		return list(self.model._default_manager.all().values())
	
	@gilbert_method
	def get(self, constraint):
		return self.model._default_manager.all().values().get(**constraint)