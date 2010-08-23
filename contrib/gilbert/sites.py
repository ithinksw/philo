from django.contrib.admin.sites import AdminSite
from django.contrib.auth import authenticate, login, logout
from django.conf.urls.defaults import url, patterns, include
from django.core.urlresolvers import reverse
from django.shortcuts import render_to_response
from django.conf import settings
from django.utils import simplejson as json
from django.utils.datastructures import SortedDict
from django.http import HttpResponse
from django.db.models.base import ModelBase
from philo.utils import fattr
from philo.contrib.gilbert.plugins import GilbertModelAdmin, GilbertPlugin, is_gilbert_method, gilbert_method
from philo.contrib.gilbert.exceptions import AlreadyRegistered, NotRegistered
from django.forms.models import model_to_dict
import sys
from traceback import format_tb
from inspect import getargspec
from django.views.decorators.cache import never_cache
from philo.contrib.gilbert import __version__ as gilbert_version
import staticmedia
import os

__all__ = ('GilbertSite', 'site')


class GilbertAuthPlugin(GilbertPlugin):
	name = 'auth'
	
	@property
	def js(self):
		return [staticmedia.url('gilbert/Gilbert.api.auth.js')]
	
	@property
	def fugue_icons(self):
		return ['user-silhouette', 'key--pencil', 'door-open-out', 'door-open-in']
	
	@gilbert_method(restricted=False)
	def login(self, request, username, password):
		user = authenticate(username=username, password=password)
		if user is not None and user.is_active:
			login(request, user)
			return True
		else:
			return False
	
	@gilbert_method
	def logout(self, request):
		logout(request)
		return True
	
	@gilbert_method
	def passwd(self, request, current_password, new_password, new_password_confirm):
		user = request.user
		if user.check_password(current_password) and (new_password == new_password_confirm):
			user.set_password(new_password)
			user.save()
			return True
		return False
	
	@gilbert_method
	def whoami(self, request):
		user = request.user
		return user.get_full_name() or user.username


class GilbertSite(object):
	version = gilbert_version
	
	def __init__(self, namespace='gilbert', app_name='gilbert', title='Gilbert'):
		self.namespace = namespace
		self.app_name = app_name
		self.title = title
		self.model_registry = SortedDict()
		self.plugin_registry = SortedDict()
		self.register_plugin(GilbertAuthPlugin)
	
	def register_plugin(self, plugin):
		if plugin.name in self.plugin_registry:
			raise AlreadyRegistered('A plugin named \'%s\' is already registered' % plugin.name)
		self.plugin_registry[plugin.name] = plugin(self)
	
	def register_model(self, model_or_iterable, admin_class=GilbertModelAdmin, **admin_attrs):
		if isinstance(model_or_iterable, ModelBase):
			model_or_iterable = [model_or_iterable]
		for model in model_or_iterable:
			if model._meta.app_label not in self.model_registry:
				self.model_registry[model._meta.app_label] = SortedDict()
			if model._meta.object_name in self.model_registry[model._meta.app_label]:
				raise AlreadyRegistered('The model %s.%s is already registered' % (model._meta.app_label, model.__name__))
			if admin_attrs:
				admin_attrs['__module__'] = __name__
				admin_class = type('%sAdmin' % model.__name__, (admin_class,), admin_attrs)
			self.model_registry[model._meta.app_label][model._meta.object_name] = admin_class(self, model)
	
	def has_permission(self, request):
		return request.user.is_active and request.user.is_staff
	
	@property
	def urls(self):
		urlpatterns = patterns('',
			url(r'^$', self.index, name='index'),
			url(r'^css$', self.css, name='css'),
			url(r'^api$', self.api, name='api'),
			url(r'^router/?$', self.router, name='router'),
			url(r'^router/models/(?P<app_label>\w+)/?$', self.router, name='models'),
			url(r'^login$', self.router, name='login'),
		)
		
		return (urlpatterns, self.app_name, self.namespace)
	
	def request_context(self, request, extra_context=None):
		from django.template import RequestContext
		context = RequestContext(request, current_app=self.namespace)
		context.update(extra_context or {})
		context.update({'gilbert': self, 'user': request.user, 'logged_in': self.has_permission(request)})
		return context
	
	@never_cache
	def index(self, request, extra_context=None):
		return render_to_response('gilbert/index.html', context_instance=self.request_context(request, extra_context))
	
	def css(self, request, extra_context=None):
		icon_names = []
		for plugin in self.plugin_registry.values():
			icon_names.extend(plugin.fugue_icons)
		
		icons = dict([(icon_name, staticmedia.url('gilbert/fugue-icons/icons/%s.png' % icon_name)) for icon_name in set(icon_names)])
		
		context = extra_context or {}
		context.update({'icons': icons})
		
		return render_to_response('gilbert/styles.css', context_instance=self.request_context(request, context), mimetype='text/css')
	
	@never_cache
	def api(self, request, extra_context=None):
		providers = []
		for app_label, models in self.model_registry.items():
			app_provider = {
				'namespace': 'Gilbert.api.models.%s' % app_label,
				'url': reverse('%s:models' % self.namespace, current_app=self.app_name, kwargs={'app_label': app_label}),
				'type': 'remoting',
			}
			model_actions = {}
			for model_name, admin in models.items():
				model_methods = []
				for method in [admin.get_method(method_name) for method_name in admin.methods]:
					if method.restricted and not self.has_permission(request):
						continue
					model_methods.append({
						'name': method.name,
						'len': method.argc,
					})
				if model_methods:
					model_actions[model_name] = model_methods
			if model_actions:
				app_provider['actions'] = model_actions
				providers.append(app_provider)
		
		plugin_provider = {
			'namespace': 'Gilbert.api',
			'url': reverse('%s:router' % self.namespace, current_app=self.app_name),
			'type': 'remoting',
		}
		plugin_actions = {}
		for plugin_name, plugin in self.plugin_registry.items():
			plugin_methods = []
			for method in [plugin.get_method(method_name) for method_name in plugin.methods]:
				if method.restricted and not self.has_permission(request):
					continue
				plugin_methods.append({
					'name': method.name,
					'len': method.argc,
				})
			if plugin_methods:
				plugin_actions[plugin_name] = plugin_methods
		if plugin_actions:
			plugin_provider['actions'] = plugin_actions
			providers.append(plugin_provider)
		
		return HttpResponse(''.join(['Ext.Direct.addProvider('+json.dumps(provider, separators=(',', ':'))+');' for provider in providers]), mimetype='text/javascript')
	
	def router(self, request, app_label=None, extra_context=None):
		submitted_form = False
		if request.META['CONTENT_TYPE'].startswith('application/x-www-form-urlencoded'):
			submitted_form = True
		
		if submitted_form:
			post_dict = dict(request.POST)
			ext_request = {
				'action': post_dict.pop('extAction'),
				'method': post_dict.pop('extMethod'),
				'type': post_dict.pop('extType'),
				'tid': post_dict.pop('extTID'),
				'upload': post_dict.pop('extUpload', False),
				'data': None,
				'kwdata': post_dict
			}
		else:
			ext_request = json.loads(request.raw_post_data)
			ext_request['upload'] = False
			ext_request['kwdata'] = None
		
		try:
			plugin = None
			
			if app_label is not None:
				try:
					plugin = self.model_registry[app_label][ext_request['action']]
				except KeyError:
					raise NotImplementedError('A model named \'%s\' has not been registered' % ext_request['action'])
			else:
				try:
					plugin = self.plugin_registry[ext_request['action']]
				except KeyError:
					raise NotImplementedError('Gilbert does not provide a class named \'%s\'' % ext_request['action'])
			
			method = plugin.get_method(ext_request['method'])
			
			if method is None or (method.restricted and not self.has_permission(request)):
				raise NotImplementedError('The method named \'%s\' is not available' % method.name)
			
			response = {'type': 'rpc', 'tid': ext_request['tid'], 'action': ext_request['action'], 'method': ext_request['method'], 'result': method(request, *(ext_request['data'] or []), **(ext_request['kwdata'] or {}))}
		except:
			exc_type, exc_value, exc_traceback = sys.exc_info()
			response = {'type': 'exception', 'tid': ext_request['tid'], 'message': ('%s: %s' % (exc_type, exc_value)), 'where': format_tb(exc_traceback)[0]}
		
		if submitted_form:
			return HttpResponse(('<html><body><textarea>%s</textarea></body></html>' % json.dumps(response)))
		return HttpResponse(json.dumps(response), content_type=('application/json; charset=%s' % settings.DEFAULT_CHARSET))


site = GilbertSite()