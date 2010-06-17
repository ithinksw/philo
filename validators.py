from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _
from django.core.validators import URLValidator
import re


class TreeParentValidator(object):
	"""
	constructor takes instance and parent_attr, where instance is the model
	being validated and parent_attr is where to look on that parent for the
	comparison.
	"""
	#message = _("A tree element can't be its own parent.")
	code = 'invalid'
	
	def __init__(self, instance, parent_attr=None, message=None, code=None):
		self.instance = instance
		self.parent_attr = parent_attr
		self.static_message = message
		if code is not None:
			self.code = code
	
	def __call__(self, value):
		"""
		Validates that the self.instance is not found in the parent tree of
		the node given as value.
		"""
		parent = value
		
		while parent:
			comparison=self.get_comparison(parent)
			if comparison == self.instance:
				# using (self.message, code=self.code) results in the admin interface
				# screwing with the error message and making it be 'Enter a valid value'
				raise ValidationError(self.message)
			parent=parent.parent
	
	def get_comparison(self, parent):
		if self.parent_attr and hasattr(parent, self.parent_attr):
			return getattr(parent, self.parent_attr)
		
		return parent
	
	def get_message(self):
		return self.static_message or _(u"A %s can't be its own parent." % self.instance.__class__.__name__)
	message = property(get_message)
	
	
class TreePositionValidator(object):
	code = 'invalid'
	
	def __init__(self, parent, slug, obj_class, message=None, code=None):
		self.parent = parent
		self.slug = slug
		self.obj_class = obj_class
		self.static_message = message
			
		if code is not None:
			self.code = code
	
	def __call__(self, value):
		"""
		Validates that there is no obj of obj_class with the same position
		as the compared obj (value) but a different id.
		"""
		if not isinstance(value, self.obj_class):
			raise ValidationError(_(u"The value must be an instance of %s." % self.obj_class.__name__))
		
		try:
			obj = self.obj_class.objects.get(slug=self.slug, parent=self.parent)
			
			if obj.id != value.id:
				raise ValidationError(self.message)
				
		except self.obj_class.DoesNotExist:
			pass
	
	def get_message(self):
		return self.static_message or _(u"A %s with that path (parent and slug) already exists." % self.obj_class.__name__)
	message = property(get_message)


class URLRedirectValidator(URLValidator):
	regex = re.compile(
        r'^(?:https?://' # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|' #domain...
        r'localhost|' #localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})' # ...or ip
        r'(?::\d+)?' # optional port
        r'|)' # also allow internal redirects
        r'(?:/?|[/?]?\S+)$', re.IGNORECASE)


class URLLinkValidator(URLValidator):
	regex = re.compile(
        r'^(?:https?://' # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|' #domain...
        r'localhost|' #localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})' # ...or ip
        r'(?::\d+)?' # optional port
        r'|)' # also allow internal links
        r'(?:/?|[/?#]?\S+)$', re.IGNORECASE)
