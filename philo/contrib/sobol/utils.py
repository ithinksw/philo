from hashlib import sha1

from django.conf import settings
from django.http import QueryDict
from django.utils.encoding import smart_str
from django.utils.http import urlquote_plus, urlquote


SEARCH_ARG_GET_KEY = 'q'
URL_REDIRECT_GET_KEY = 'url'
HASH_REDIRECT_GET_KEY = 's'


def make_redirect_hash(search_arg, url):
	"""Hashes a redirect for a ``search_arg`` and ``url`` to avoid providing a simple URL spoofing service."""
	return sha1(smart_str(search_arg + url + settings.SECRET_KEY)).hexdigest()[::2]


def check_redirect_hash(hash, search_arg, url):
	"""Checks whether a hash is valid for a given ``search_arg`` and ``url``."""
	return hash == make_redirect_hash(search_arg, url)


def make_tracking_querydict(search_arg, url):
	"""Returns a :class:`QueryDict` instance containing the information necessary for tracking :class:`.Click`\ s on the ``url``."""
	return QueryDict("%s=%s&%s=%s&%s=%s" % (
		SEARCH_ARG_GET_KEY, urlquote_plus(search_arg),
 		URL_REDIRECT_GET_KEY, urlquote(url),
		HASH_REDIRECT_GET_KEY, make_redirect_hash(search_arg, url))
	)


class RegistryIterator(object):
	def __init__(self, registry, iterattr='__iter__', transform=lambda x:x):
		if not hasattr(registry, iterattr):
			raise AttributeError("Registry has no attribute %s" % iterattr)
		self.registry = registry
		self.iterattr = iterattr
		self.transform = transform
	
	def __iter__(self):
		return self
	
	def next(self):
		if not hasattr(self, '_iter'):
			self._iter = getattr(self.registry, self.iterattr)()
		
		return self.transform(self._iter.next())
	
	def copy(self):
		return self.__class__(self.registry, self.iterattr, self.transform)