from django.conf import settings
from django.contrib.auth import authenticate, login
from django.core.context_processors import csrf
from django.conf.urls.defaults import url, patterns, include
from django.core.urlresolvers import reverse
from django.db.models.base import ModelBase
from django.forms.models import model_to_dict
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.utils import simplejson as json
from django.utils.datastructures import SortedDict
from django.views.decorators.cache import never_cache
from philo.utils import fattr
from . import __version__ as gilbert_version
from .exceptions import AlreadyRegistered, NotRegistered
from .extdirect import ExtAction, ExtRouter
from .plugins.auth import Auth
from .plugins.models import Models, ModelAdmin
from inspect import getargspec
from functools import partial, update_wrapper
import sys, os, datetime



__all__ = ('GilbertSite', 'site')


class CoreRouter(ExtRouter):
	def __init__(self, site):
		self.site = site
		self._actions = {}
	
	@property
	def namespace(self):
		return 'Gilbert.api.plugins'
	
	@property
	def url(self):
		return reverse('%s:router' % self.site.namespace, current_app=self.site.app_name)
	
	@property
	def type(self):
		return 'remoting'
	
	@property
	def actions(self):
		return self._actions
	
	@property
	def plugins(self):
		return list(action.obj for action in self._actions.itervalues())
	
	def register_plugin(self, plugin):
		action = ExtAction(plugin)
		self._actions[action.name] = action


class ModelRouter(ExtRouter):
	def __init__(self, site, app_label):
		self.site = site
		self.app_label = app_label
		self._actions = {}
	
	@property
	def namespace(self):
		return 'Gilbert.api.models.%s' % self.app_label
	
	@property
	def url(self):
		return reverse('%s:model_router' % self.site.namespace, current_app=self.site.app_name, kwargs={'app_label': self.app_label})
	
	@property
	def type(self):
		return 'remoting'
	
	@property
	def actions(self):
		return self._actions
	
	@property
	def models(self):
		return dict((name, action.obj) for name, action in self._actions.iteritems())
	
	def register_admin(self, name, admin):
		action = ExtAction(admin)
		action.name = name
		self._actions[action.name] = action


class GilbertSite(object):
	version = gilbert_version
	
	def __init__(self, namespace='gilbert', app_name='gilbert', title=None):
		self.namespace = namespace
		self.app_name = app_name
		if title is None:
			self.title = getattr(settings, 'GILBERT_TITLE', 'Gilbert')
		else:
			self.title = title
		
		self.core_router = CoreRouter(self)
		self.model_routers = SortedDict()
		
		self.register_plugin(Models)
		self.register_plugin(Auth)
	
	def register_plugin(self, plugin):
		self.core_router.register_plugin(plugin(self))
	
	def register_model(self, model_or_iterable, admin_class=ModelAdmin, **admin_attrs):
		if isinstance(model_or_iterable, ModelBase):
			model_or_iterable = [model_or_iterable]
		for model in model_or_iterable:
			app_label = model._meta.app_label
			name = model._meta.object_name
			
			if app_label not in self.model_routers:
				self.model_routers[app_label] = ModelRouter(self, app_label)
			router = self.model_routers[app_label]
			
			if admin_attrs:
				admin_attrs['__module__'] = __name__
				admin_class = type('%sAdmin' % model.__name__, (admin_class,), admin_attrs)
			
			router.register_admin(name, admin_class(self, model))
	
	def has_permission(self, request):
		return request.user.is_active and request.user.is_staff
	
	def protected_view(self, view, login_page=True, cacheable=False):
		def inner(request, *args, **kwargs):
			if not self.has_permission(request):
				if login_page:
					return self.login(request)
				else:
					return HttpResponse(status=403)
			return view(request, *args, **kwargs)
		if not cacheable:
			inner = never_cache(inner)
		return update_wrapper(inner, view)
	
	@property
	def urls(self):
		urlpatterns = patterns('',
			url(r'^$', self.protected_view(self.index), name='index'),
			url(r'^api.js$', self.protected_view(self.api, login_page=False), name='api'),
			url(r'^icons.css$', self.protected_view(self.icons, login_page=False), name='icons'),
			url(r'^router$', self.protected_view(self.router, login_page=False), name='router'),
			url(r'^router/models/(?P<app_label>\w+)$', self.protected_view(self.router, login_page=False), name='model_router'),
		)
		return (urlpatterns, self.app_name, self.namespace)
	
	def login(self, request):
		context = {
			'gilbert': self,
			'form_url': request.get_full_path(),
		}
		context.update(csrf(request))
		
		if request.POST:
			if request.session.test_cookie_worked():
				request.session.delete_test_cookie()
				username = request.POST.get('username', None)
				password = request.POST.get('password', None)
				user = authenticate(username=username, password=password)
				if user is not None:
					if user.is_active and user.is_staff:
						login(request, user)
						return HttpResponseRedirect(request.get_full_path())
					else:
						context.update({
							'error_message_short': 'Not staff',
							'error_message': 'You do not have access to this page.',
						})
				else:
					context.update({
						'error_message_short': 'Invalid credentials',
						'error_message': 'Unable to authenticate using the provided credentials. Please try again.',
					})
			else:
				context.update({
					'error_message_short': 'Cookies disabled',
					'error_message': 'Please enable cookies, reload this page, and try logging in again.',
				})
		
		request.session.set_test_cookie()
		return render_to_response('gilbert/login.html', context, context_instance=RequestContext(request))
	
	def index(self, request):
		return render_to_response('gilbert/index.html', {
			'gilbert': self,
			'plugins': self.core_router.plugins # needed as the template language will not traverse callables
		}, context_instance=RequestContext(request))
	
	def api(self, request):
		providers = []
		model_registry = {}
		
		for app_label, router in self.model_routers.items():
			if request.user.has_module_perms(app_label):
				providers.append(router.spec)
				model_registry[app_label] = dict((model_name, admin) for model_name, admin in router.models.items() if admin.has_permission(request))
		
		providers.append(self.core_router.spec)
		
		context = {
			'gilbert': self,
			'providers': [json.dumps(provider, separators=(',', ':')) for provider in providers],
			'model_registry': model_registry,
		}
		context.update(csrf(request))
		
		return render_to_response('gilbert/api.js', context, mimetype='text/javascript')
	
	def icons(self, request):
		icon_names = []
		
		for plugin in self.core_router.plugins:
			icon_names.extend(plugin.icon_names)
		
		for router in self.model_routers.values():
			for admin in router.models.values():
				icon_names.extend(admin.icon_names)
		
		return render_to_response('gilbert/icons.css', {
			'icon_names': set(icon_names),
			'STATIC_URL': settings.STATIC_URL
		}, mimetype='text/css')
	
	def router(self, request, app_label=None, extra_context=None):
		if app_label is None:
			return self.core_router.render_to_response(request)
		else:
			return self.model_routers[app_label].render_to_response(request)


site = GilbertSite()