from django.contrib.admin.sites import AdminSite
from django.contrib.auth import authenticate, login, logout
from django.conf.urls.defaults import url, patterns
from django.core.urlresolvers import reverse
from django.shortcuts import render_to_response
from django.conf import settings
from django.utils import simplejson as json
from django.utils.datastructures import SortedDict
from django.http import HttpResponse
from django.db.models.base import ModelBase
from philo.utils import fattr
from philo.contrib.gilbert.options import GilbertModelAdmin, GilbertPlugin, GilbertClass
from philo.contrib.gilbert.exceptions import AlreadyRegistered, NotRegistered
from django.forms.models import model_to_dict
import sys
from traceback import format_tb
from inspect import getargspec
from philo.contrib.gilbert.utils import is_gilbert_plugin, is_gilbert_class, is_gilbert_method, gilbert_method, call_gilbert_method


__all__ = ('GilbertSite', 'site')


class GilbertSitePlugin(GilbertPlugin):
	class auth(GilbertClass):
		@gilbert_method(restricted=False)
		def login(self, request, username, password):
			user = authenticate(username=username, password=password)
			if user is not None and user.is_active:
				login(request, user)
				return True
			else:
				return False
		
		@gilbert_method(restricted=False)
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


class GilbertSite(object):
	def __init__(self, namespace='gilbert', app_name='gilbert', title='Gilbert'):
		self.namespace = namespace
		self.app_name = app_name
		self.title = title
		self.core_api = GilbertSitePlugin(self)
		self.model_registry = SortedDict()
		self.plugin_registry = SortedDict()
	
	def register_plugin(self, plugin):
		if is_gilbert_plugin(plugin):
			if plugin.gilbert_plugin_name in self.plugin_registry:
				raise AlreadyRegistered('A plugin named \'%s\' is already registered' % plugin.gilbert_plugin_name)
			self.plugin_registry[plugin.gilbert_plugin_name] = plugin(self)
		else:
			raise ValueError('register_plugin must be provided a valid plugin class or instance')
	
	def register_model(self, model_or_iterable, admin_class=GilbertModelAdmin, **admin_attrs):
		if isinstance(model_or_iterable, ModelBase):
			model_or_iterable = [model_or_iterable]
		for model in model_or_iterable:
			if model._meta.app_label not in self.model_registry:
				self.model_registry[model._meta.app_label] = SortedDict()
			if model._meta.object_name in self.model_registry[model._meta.app_label]:
				raise AlreadyRegistered('The model %s is already registered' % model.__name__)
			if admin_attrs:
				admin_attrs['__module__'] = __name__
				admin_class = type('%sAdmin' % model.__name__, (admin_class,), admin_attrs)
			self.model_registry[model._meta.app_label][model._meta.object_name] = admin_class(self, model)
	
	def has_permission(self, request):
		return request.user.is_active and request.user.is_staff
	
	@property
	def urls(self):
		return (patterns('',
			url(r'^$', self.index, name='index'),
			url(r'^css.css$', self.css, name='css'),
			url(r'^api.js$', self.api, name='api'),
			url(r'^router/?$', self.router, name='router'),
			url(r'^models/(?P<app_label>\w+)/?$', self.router, name='models'),
			url(r'^plugins/(?P<plugin_name>\w+)/?$', self.router, name='plugins'),
			url(r'^login$', self.router, name='login'),
		), self.app_name, self.namespace)
	
	def request_context(self, request, extra_context=None):
		from django.template import RequestContext
		context = RequestContext(request, current_app=self.namespace)
		context.update(extra_context or {})
		context.update({'gilbert': self, 'user': request.user, 'logged_in': self.has_permission(request)})
		return context
	
	def index(self, request, extra_context=None):
		return render_to_response('gilbert/index.html', context_instance=self.request_context(request, extra_context))
	
	def css(self, request, extra_context=None):
		return render_to_response('gilbert/css.css', context_instance=self.request_context(request, extra_context), mimetype='text/css')
	
	def api(self, request, extra_context=None):
		return render_to_response('gilbert/api.js', context_instance=self.request_context(request, extra_context), mimetype='text/javascript')
	
	def router(self, request, app_label=None, plugin_name=None, extra_context=None):
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
				'data': None,
				'kwdata': post_dict,
			}
			if 'extUpload' in request.POST:
				ext_request['upload'] = request.POST['extUpload']
		else:
			ext_request = json.loads(request.raw_post_data)
			ext_request['kwdata'] = None
		
		try:
			gilbert_class = None
			
			if app_label is not None:
				try:
					gilbert_class = self.model_registry[app_label][ext_request['action']]
				except KeyError:
					raise NotImplementedError('A model named \'%s\' has not been registered' % ext_request['action'])
			elif plugin_name is not None:
				try:
					gilbert_plugin = self.plugin_registry[plugin_name]
				except KeyError:
					raise NotImplementedError('A plugin named \'%s\' has not been registered' % plugin_name)
				try:
					gilbert_class = gilbert_plugin.gilbert_plugin_classes[ext_request['action']]
				except KeyError:
					raise NotImplementedError('The plugin named \'%s\' does not provide a class named \'%s\'' % (plugin_name, ext_request['action']))
			else:
				try:
					gilbert_class = self.core_api.gilbert_plugin_classes[ext_request['action']]
				except KeyError:
					raise NotImplementedError('Gilbert does not provide a class named \'%s\'' % ext_request['action'])
			
			try:
				method = gilbert_class.gilbert_class_methods[ext_request['method']]
			except KeyError:
				raise NotImplementedError('The class named \'%s\' does not implement a method named \'%\'' % (gilbert_class.gilbert_class_name, ext_request['method']))
			if method.gilbert_method_restricted and not self.has_permission(request):
				raise NotImplementedError('The method named \'%s\' is not available' % method.gilbert_method_name)
			response = {'type': 'rpc', 'tid': ext_request['tid'], 'action': ext_request['action'], 'method': ext_request['method'], 'result': call_gilbert_method(method, gilbert_class, request, *(ext_request['data'] or []), **(ext_request['kwdata'] or {}))}
		except:
			exc_type, exc_value, exc_traceback = sys.exc_info()
			response = {'type': 'exception', 'tid': ext_request['tid'], 'message': ('%s: %s' % (exc_type, exc_value)), 'where': format_tb(exc_traceback)[0]}
		
		if submitted_form:
			return HttpResponse(('<html><body><textarea>%s</textarea></body></html>' % json.dumps(response)))
		return HttpResponse(json.dumps(response), content_type=('application/json; charset=%s' % settings.DEFAULT_CHARSET))


site = GilbertSite()