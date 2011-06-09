from django.conf import settings
from django.http import QueryDict
from django.utils.encoding import smart_str
from django.utils.http import urlquote_plus, urlquote
from hashlib import sha1


SEARCH_ARG_GET_KEY = 'q'
URL_REDIRECT_GET_KEY = 'url'
HASH_REDIRECT_GET_KEY = 's'


def make_redirect_hash(search_arg, url):
	return sha1(smart_str(search_arg + url + settings.SECRET_KEY)).hexdigest()[::2]


def check_redirect_hash(hash, search_arg, url):
	return hash == make_redirect_hash(search_arg, url)


def make_tracking_querydict(search_arg, url):
	"""
	Returns a QueryDict instance containing the information necessary
	for tracking clicks of this url.
	
	NOTE: will this kind of initialization handle quoting correctly?
	"""
	return QueryDict("%s=%s&%s=%s&%s=%s" % (
		SEARCH_ARG_GET_KEY, urlquote_plus(search_arg),
 		URL_REDIRECT_GET_KEY, urlquote(url),
		HASH_REDIRECT_GET_KEY, make_redirect_hash(search_arg, url))
	)