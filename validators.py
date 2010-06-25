from django.utils.translation import ugettext_lazy as _
from django.core.validators import RegexValidator
import re


class RedirectValidator(RegexValidator):
	"""Based loosely on the URLValidator, but no option to verify_exists"""
	regex = re.compile(
		r'^(?:https?://' # http:// or https://
		r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|' #domain...
		r'localhost|' #localhost...
		r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})' # ...or ip
		r'(?::\d+)?' # optional port
		r'(?:/?|[/?#]?\S+)|'
		r'[^?#\s]\S*)$',
		re.IGNORECASE)
	message = _(u'Enter a valid absolute or relative redirect target')


class URLLinkValidator(RegexValidator):
	"""Based loosely on the URLValidator, but no option to verify_exists"""
	regex = re.compile(
		r'^(?:https?://' # http:// or https://
		r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|' #domain...
		r'localhost|' #localhost...
		r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})' # ...or ip
		r'(?::\d+)?' # optional port
		r'|)' # also allow internal links
		r'(?:/?|[/?#]?\S+)$', re.IGNORECASE)
	message = _(u'Enter a valid absolute or relative redirect target')
