def fattr(*args, **kwargs):
	def wrapper(function):
		for key in kwargs:
			setattr(function, key, kwargs[key])
		return function
	return wrapper
