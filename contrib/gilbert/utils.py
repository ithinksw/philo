from inspect import isclass, getargspec


def is_gilbert_plugin(class_or_instance):
	from philo.contrib.gilbert.options import GilbertPluginBase, GilbertPlugin
	return (isclass(class_or_instance) and issubclass(class_or_instance, GilbertPlugin)) or isinstance(class_or_instance, GilbertPlugin) or (getattr(class_or_instance, '__metaclass__', None) is GilbertPluginBase) or (getattr(class_or_instance, 'gilbert_plugin', False) and (getattr(class_or_instance, 'gilbert_plugin_name', None) is not None) and (getattr(class_or_instance, 'gilbert_plugin_classes', None) is not None))


def is_gilbert_class(class_or_instance):
	from philo.contrib.gilbert.options import GilbertClassBase, GilbertClass
	return (isclass(class_or_instance) and issubclass(class_or_instance, GilbertClass)) or isinstance(class_or_instance, GilbertClass) or (getattr(class_or_instance, '__metaclass__', None) is GilbertClassBase) or (getattr(class_or_instance, 'gilbert_class', False) and (getattr(class_or_instance, 'gilbert_class_name', None) is not None) and (getattr(class_or_instance, 'gilbert_class_methods', None) is not None))


def is_gilbert_method(function):
	return getattr(function, 'gilbert_method', False)


def gilbert_method(function=None, name=None, argc=None, restricted=True):
	def wrapper(function):
		setattr(function, 'gilbert_method', True)
		setattr(function, 'gilbert_method_name', name or function.__name__)
		setattr(function, 'gilbert_method_restricted', restricted)
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
		setattr(function, 'gilbert_method_argc', new_argc)
		return function
	if function is not None:
		return wrapper(function)
	return wrapper


def call_gilbert_method(method, cls, request, *args, **kwargs):
	arg_list = getargspec(method)[0]
	if len(arg_list) > 0:
		if arg_list[0] == 'self':
			if len(arg_list) > 1 and arg_list[1] == 'request':
				return method(cls, request, *args, **kwargs)
			return method(cls, *args, **kwargs)
		elif arg_list[0] == 'request':
			return method(request, *args, **kwargs)
	else:
		return method(*args, **kwargs)