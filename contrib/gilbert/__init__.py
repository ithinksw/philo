from philo.contrib.gilbert.sites import GilbertSite, site


def autodiscover():
	import copy
	from django.conf import settings
	from django.utils.importlib import import_module
	from django.utils.module_loading import module_has_submodule
	
	for app in settings.INSTALLED_APPS:
		mod = import_module(app)
		try:
			before_import_model_registry = copy.copy(site.model_registry)
			before_import_plugin_registry = copy.copy(site.plugin_registry)
			import_module('%s.gilbert' % app)
		except:
			site.model_registry = before_import_model_registry
			site.plugin_registry = before_import_plugin_registry
			
			if module_has_submodule(mod, 'gilbert'):
				raise