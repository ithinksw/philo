"""
Sobol implements a generic search interface, which can be used to search databases or websites. No assumptions are made about the search method. If SOBOL_USE_CACHE is ``True`` (default), the results will be cached using django's cache framework. Be aware that this may use a large number of cache entries, as a unique entry will be made for each search string for each type of search.

Settings
--------

:setting:`SOBOL_USE_CACHE`
	Whether sobol will use django's cache framework. Defaults to ``True``; this may cause a lot of entries in the cache.

:setting:`SOBOL_USE_EVENTLET`
	If :mod:`eventlet` is installed and this setting is ``True``, sobol web searches will use :mod:`eventlet.green.urllib2` instead of the built-in :mod:`urllib2` module. Default: ``False``.

"""

from philo.contrib.sobol.search import *