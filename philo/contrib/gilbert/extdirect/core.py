from django.db.models import Q
from django.http import HttpResponse
from django.utils import simplejson as json
from django.utils.encoding import smart_str
from django.views.debug import ExceptionReporter
from inspect import isclass, ismethod, isfunction, getmembers, getargspec
from traceback import format_tb
from abc import ABCMeta, abstractproperty
from collections import Callable, Sized, Mapping
import sys, datetime


# __all__ = ('ext_action', 'ext_method', 'is_ext_action', 'is_ext_method', 'ExtAction', 'ExtMethod')


class ExtRequest(object):
	"""
	Represents a single Ext.Direct request along with the :class:`django.http.HttpRequest` it originates from.
	
	.. note::
		
		Passes undefined attribute accesses through to the underlying :class:`django.http.HttpRequest`.
	
	"""
	
	@classmethod
	def parse(cls, request, object_hook=None):
		"""
		Parses Ext.Direct request(s) from the originating HTTP request.
		
		:arg request: the originating HTTP request
		:type request: :class:`django.http.HttpRequest`
		:returns: list of :class:`ExtRequest` instances
		
		"""
		
		requests = []
		
		if request.META['CONTENT_TYPE'].startswith('application/x-www-form-urlencoded') or request.META['CONTENT_TYPE'].startswith('multipart/form-data'):
			requests.append(cls(request,
				type = request.POST.get('extType'),
				tid = request.POST.get('extTID'),
				action = request.POST.get('extAction'),
				method = request.POST.get('extMethod'),
				data = request.POST.get('extData', None),
				upload = True if request.POST.get('extUpload', False) in (True, 'true', 'True') else False,
				form_request = True,
			))
		else:
			decoded_requests = json.loads(request.raw_post_data, object_hook=object_hook)
			if type(decoded_requests) is dict:
				decoded_requests = [decoded_requests]
			for inner_request in decoded_requests:
				requests.append(cls(request,
					type = inner_request.get('type'),
					tid = inner_request.get('tid'),
					action = inner_request.get('action'),
					method = inner_request.get('method'),
					data = inner_request.get('data', None),
				))
		
		return requests
	
	def __init__(self, request, type, tid, action, method, data, upload=False, form_request=False):
		"""
		:arg request: the originating HTTP request
		:type request: :class:`django.http.HttpRequest`
		:arg type: Ext.Direct request type
		:type type: str
		:arg tid: Ext.Direct transaction identifier
		:type tid: str
		:arg action: Ext.Direct action name
		:type action: str
		:arg method: Ext.Direct method name
		:type method: str
		:arg data: Ext.Direct method arguments
		:type data: list
		:arg upload: request includes uploaded file(s)
		:type upload: bool
		:arg form_request: request made by form submission
		:type form_request: bool
		
		"""
		
		self.type = type
		self.tid = tid
		self.request = request
		self.action = action
		self.method = method
		self.data = data if data is not None else []
		self.upload = upload
		self.form_request = form_request
	
	def __getattr__(self, key):
		try:
			return getattr(self.request, key)
		except:
			raise AttributeError


class ExtMethod(Callable, Sized):
	"""
	Wraps a (previously :meth:`decorated <ExtMethod.decorate>`) function as an Ext.Direct method.
	
	"""
	
	@classmethod
	def decorate(cls, function=None, name=None, form_handler=False):
		"""
		Applies metadata to function identifying it as wrappable, or returns a decorator for doing the same::
		
			@ExtMethod.decorate
			def method(self, request):
				pass
			
			@ExtMethod.decorate(name='custom_name', form_handler=True)
			def form_handler_with_custom_name(self, request):
				pass
		
		Intended for use on methods of classes already decorated by :meth:`ExtAction.decorate`.
		
		:arg name: custom Ext.Direct method name
		:type name: str
		:arg form_handler: function handles form submissions
		:type form_handler: bool
		:returns: function with metadata applied
		
		"""
		
		def setter(function):
			setattr(function, '_ext_method', True)
			setattr(function, '_ext_method_form_handler', form_handler)
			if name is not None:
				setattr(function, '_ext_method_name', name)
			return function
		if function is not None:
			return setter(function)
		return setter
	
	@classmethod
	def validate(cls, function):
		"""
		Validates that function has been :meth:`decorated <ExtMethod.decorate>` and is therefore wrappable.
		
		"""
		
		return getattr(function, '_ext_method', False)
	
	def __init__(self, function):
		"""
		:arg function: function to wrap
		:type function: callable
		
		If the function accepts variable positional arguments, the Ext.Direct method argument count will be increased by one for acceptance of a list.
		
		Similarly, if the function accepts variable keyword arguments, the argument count will be increased by one for acceptance of a dictionary.
		
		.. warning::
			
			Wrapped functions **must** accept at least one positional argument (in addition to self if function is a method): the :class:`ExtRequest` that caused the invocation.
		
		.. warning::
			
			Wrapped functions identified as handling form submissions **must** return a tuple containing:
			
			* a boolean indicating success or failure
			* a dictionary of fields mapped to errors, if any, or None
		
		"""
		self.function = function
		self.form_handler = getattr(function, '_ext_method_form_handler', False)
		self.name = getattr(function, '_ext_method_name', function.__name__)
		
		argspec = getargspec(self.function)
		len_ = len(argspec.args)
		
		if len_ >= 2 and ismethod(self.function):
			len_ -= 2
		elif len_ >= 1 and not ismethod(self.function):
			len_ -= 1
		else:
			raise TypeError('%s cannot be wrapped as an Ext.Direct method as it does not take an ExtRequest as its first positional argument')
		
		if argspec.varargs is not None:
			len_ += 1
			self.accepts_varargs = True
		else:
			self.accepts_varargs = False
		
		if argspec.keywords is not None:
			len_ += 1
			self.accepts_keywords = True
		else:
			self.accepts_keywords = False
		
		self.len = len_
	
	@property
	def spec(self):
		return {
			'name': self.name,
			'len': self.len,
			'formHandler': self.form_handler
		}
	
	def __len__(self):
		return self.len
	
	def __call__(self, request):
		"""
		Invoke the wrapped function using the provided :class:`ExtRequest` and return the raw result.
		
		:arg request: the :class:`ExtRequest`
		
		:raises TypeError: the request did not provide the required number of arguments
		:raises Exception: the (form handling) function did not return a valid result for a form submission request
		
		"""
		
		args = request.data
		args_len = len(args)
		
		if args_len != self.len:
			raise TypeError('%s takes exactly %i arguments (%i given)' % (self.name, self.len, args_len))
		
		keywords = {}
		if self.accepts_keywords:
			keywords = dict([(smart_str(k, 'ascii'), v) for k,v in args.pop().items()])
		
		varargs = []
		if self.accepts_varargs:
			varargs = args.pop()
		
		result = self.function(request, *(args + varargs), **keywords)
		
		if self.form_handler:
			try:
				new_result = {
					'success': result[0],
					'errors': result[1],
				}
				if len(result) > 2:
					new_result['pk'] = result[2]
				
				if new_result['success']:
					del new_result['errors']
				
				result = new_result
			except:
				raise Exception # pick a better one
		
		return result


ext_method = ExtMethod.decorate
"""
Convenience alias for :meth:`ExtMethod.decorate`.

"""


is_ext_method = ExtMethod.validate
"""
Convenience alias for :meth:`ExtMethod.validate`.

"""


class ExtAction(Callable, Mapping):
	"""
	Wraps a (previously :meth:`decorated <ExtAction.decorate>`) object as an Ext.Direct action.
	
	"""
	
	method_class = ExtMethod
	"""
	The :class:`ExtMethod` subclass used when wrapping the wrapped object's members.
	
	"""
	
	@classmethod
	def decorate(cls, obj=None, name=None):
		"""
		Applies metadata to obj identifying it as wrappable, or returns a decorator for doing the same::
		
			@ExtAction.decorate
			class MyAction(object):
				pass
			
			@ExtAction.decorate(name='GoodAction')
			class BadAction(object):
				pass
		
		Intended for use on classes with member functions (methods) already decorated with :meth:`ExtMethod.decorate`.
		
		:arg name: custom Ext.Direct action name
		:type name: str
		:returns: obj with metadata applied
		
		"""
		
		def setter(obj):
			setattr(obj, '_ext_action', True)
			if name is not None:
				setattr(obj, '_ext_action_name', name)
			return obj
		if obj is not None:
			return setter(obj)
		return setter
	
	@classmethod
	def validate(cls, obj):
		"""
		Validates that obj has been :meth:`decorated <ExtAction.decorate>` and is therefore wrappable.
		
		"""
		
		return getattr(obj, '_ext_action', False)
	
	def __init__(self, obj):
		self.obj = obj
		self.name = getattr(obj, '_ext_action_name', obj.__name__ if isclass(obj) else obj.__class__.__name__)
		self._methods = None
	
	@property
	def methods(self):
		if not self._methods:
			self._methods = dict((method.name, method) for method in (self.method_class(member) for name, member in getmembers(self.obj, self.method_class.validate)))
		return self._methods
	
	def __len__(self):
		return len(self.methods)
	
	def __iter__(self):
		return iter(self.methods)
	
	def __getitem__(self, name):
		return self.methods[name]
		
	@property
	def spec(self):
		"""
		Returns a tuple containing:
			
			* the action name
			* a list of :class:`method specs <ExtMethod.spec>`
		
		Used internally by :class:`providers <ExtProvider>` to construct an Ext.Direct provider spec.
		
		"""
		
		return self.name, list(method.spec for method in self.itervalues())
	
	def __call__(self, request):
		return self[request.method](request)


ext_action = ExtAction.decorate
"""
Convenience alias for :meth:`ExtAction.decorate`.

"""


is_ext_action = ExtAction.validate
"""
Convenience alias for :meth:`ExtAction.validate`.

"""


class ExtResponse(object):
	"""
	Abstract base class for responses to :class:`requests <ExtRequest>`.
	
	"""
	__metaclass__ = ABCMeta
	
	@abstractproperty
	def as_ext(self):
		raise NotImplementedError


class ExtResult(ExtResponse):
	"""
	Represents a successful response to a :class:`request <ExtRequest>`.
	
	"""
	
	def __init__(self, request, result):
		"""
		:arg request: the originating Ext.Direct request
		:type request: :class:`ExtRequest`
		:arg result: the raw result
		
		"""
		self.request = request
		self.result = result
	
	@property
	def as_ext(self):
		return {
			'type': self.request.type,
			'tid': self.request.tid,
			'action': self.request.action,
			'method': self.request.method,
			'result': self.result
		}


class ExtException(ExtResponse):
	"""
	Represents an exception raised by an unsuccessful response to a :class:`request <ExtRequest>`.
	
	.. warning::
		
		If :data:`django.conf.settings.DEBUG` is True, information about which exception was raised and where it was raised (including a traceback in both plain text and HTML) will be provided to the client.
	
	"""
	
	def __init__(self, request, exc_info):
		"""
		
		"""
		self.request = request
		self.exc_info = exc_info
	
	@property
	def as_ext(self):
		from django.conf import settings
		if settings.DEBUG:
			reporter = ExceptionReporter(self.request.request, *self.exc_info)
			return {
				'type': 'exception',
				'tid': self.request.tid,
				'message': '%s: %s' % (self.exc_info[0], self.exc_info[1]),
				'where': format_tb(self.exc_info[2])[0],
				'identifier': '%s.%s' % (self.exc_info[0].__module__, self.exc_info[0].__name__),
				'html': reporter.get_traceback_html()
			}
		else:
			return {
				'type': 'exception',
				'tid': self.request.tid
			}


class ExtProvider(Callable, Mapping):
	"""
	Abstract base class for Ext.Direct provider implementations.
	
	"""
	
	__metaclass__ = ABCMeta
	
	result_class = ExtResult
	"""
	The :class:`ExtResponse` subclass used to represent the results of a successful Ext.Direct method invocation.
	
	"""
	
	exception_class = ExtException
	"""
	The :class:`ExtResponse` subclass used to represent the exception raised during an unsuccessful Ext.Direct method invocation.
	
	"""
	
	@abstractproperty
	def namespace(self):
		"""
		The Ext.Direct provider namespace.
		
		"""
		raise NotImplementedError
	
	@abstractproperty
	def url(self):
		"""
		The Ext.Direct provider url.
		
		"""
		raise NotImplementedError
	
	@abstractproperty
	def type(self):
		"""
		The Ext.Direct provider type.
		
		"""
		raise NotImplementedError
	
	@abstractproperty
	def actions(self):
		"""
		The dictionary of action names and :class:`ExtAction` instances handled by the provider.
		
		"""
		raise NotImplementedError
	
	def __len__(self):
		return len(self.actions)
	
	def __iter__(self):
		return iter(self.actions)
	
	def __getitem__(self, name):
		return self.actions[name]
	
	@property
	def spec(self):
		return {
			'namespace': self.namespace,
			'url': self.url,
			'type': self.type,
			'actions': dict(action.spec for action in self.itervalues())
		}
	
	def __call__(self, request):
		"""
		Returns a :class:`response <ExtResponse>` to the :class:`request <ExtRequest>`.
		
		"""
		try:
			return self.result_class(request=request, result=self[request.action](request))
		except Exception:
			return self.exception_class(request=request, exc_info=sys.exc_info())


class ExtRouter(ExtProvider):
	"""
	A :class:`provider <ExtProvider>` base class with an implementation capable of handling the complete round-trip from a :class:`django.http.HttpRequest` to a :class:`django.http.HttpResponse`.
	
	"""
	
	__metaclass__ = ABCMeta
	
	request_class = ExtRequest
	"""
	The :class:`ExtRequest` subclass used parse and to represent the individual Ext.Direct requests within a :class:`django.http.HttpRequest`.
	
	"""
	
	@classmethod
	def json_object_hook(cls, obj):
		if obj.get('q_object', False):
			return Q._new_instance(obj['children'], obj['connector'], obj['negated'])
		return obj
	
	@classmethod
	def json_default(cls, obj):
		from django.forms.models import ModelChoiceIterator
		from django.db.models.query import ValuesListQuerySet
		from django.utils.functional import Promise
		
		if isinstance(obj, ExtResponse):
			return obj.as_ext
		elif isinstance(obj, datetime.datetime):
			obj = obj.replace(microsecond=0)
			return obj.isoformat(' ')
		elif isinstance(obj, ModelChoiceIterator) or isinstance(obj, ValuesListQuerySet):
			return list(obj)
		elif isinstance(obj, Promise):
			return unicode(obj)
		elif isinstance(obj, Q):
			return {
				'q_object': True,
				'connector': obj.connector,
				'negated': obj.negated,
				'children': obj.children
			}
		else:
			raise TypeError, 'Object of type %s with value of %s is not JSON serializable' % (type(obj), repr(obj))
	
	def render_to_response(self, request):
		"""
		Returns a :class:`django.http.HttpResponse` containing the :class:`response(s) <ExtResponse>` to the :class:`request(s) <ExtRequest>` in the provided :class:`django.http.HttpRequest`.
		
		"""
		
		from django.conf import settings
		
		requests = self.request_class.parse(request, object_hook=self.json_object_hook)
		responses = []
		html_response = False
		
		for request in requests:
			if request.form_request and request.upload:
				html_response = True
			responses.append(self(request))
		
		response = responses[0] if len(responses) == 1 else responses
		json_response = json.dumps(responses, default=self.json_default)
		
		if html_response:
			return HttpResponse('<html><body><textarea>%s</textarea></body></html>' % json_response)
		return HttpResponse(json_response, content_type='application/json; charset=%s' % settings.DEFAULT_CHARSET)


class SimpleExtRouter(ExtRouter):
	"""
	A simple concrete :class:`router <ExtRouter>` implementation.
	
	"""
	
	def __init__(self, namespace, url, actions=None, type='remoting'):
		"""
		:arg namespace: the Ext.Direct provider namespace
		:type namespace: str
		:arg url: the Ext.Direct provider url
		:type url: str
		:arg actions: the dictionary of action names and :class:`ExtAction` instances handled by the provider
		:type actions: dict
		:arg type: the Ext.Direct provider type
		:type type: str
		
		"""
		
		self._type = type
		self._namespace = namespace
		self._url = url
		self._actions = actions if actions is not None else {}
	
	@property
	def namespace(self):
		return self._namespace
	
	@property
	def url(self):
		return self._url
	
	@property
	def type(self):
		return self._type
	
	@property
	def actions(self):
		return self._actions