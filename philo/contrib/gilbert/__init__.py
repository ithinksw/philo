__version__ = 'alpha'


from philo.contrib.gilbert.sites import GilbertSite, site


def autodiscover():
	import copy
	from django.conf import settings
	from django.utils.importlib import import_module
	from django.utils.module_loading import module_has_submodule
	
	for app in settings.INSTALLED_APPS:
		mod = import_module(app)
		try:
			before_import_model_routers = copy.copy(site.model_routers)
			before_import_core_router = copy.copy(site.core_router)
			import_module('%s.gilbert' % app)
		except:
			site.model_routers = before_import_model_routers
			site.core_router = before_import_core_router
			
			if module_has_submodule(mod, 'gilbert'):
				raise