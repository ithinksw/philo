"""
Sobol implements a generic search interface, which can be used to search databases or websites. No assumptions are made about the search method. If SOBOL_USE_CACHE is ``True`` (default), the results will be cached using django's cache framework. Be aware that this may use a large number of cache entries, as a unique entry will be made for each search string for each type of search.

Settings
--------

:setting:`SOBOL_USE_CACHE`
	Whether sobol will use django's cache framework. Defaults to ``True``; this may cause a lot of entries in the cache.

:setting:`SOBOL_USE_EVENTLET`
	If :mod:`eventlet` is installed and this setting is ``True``, sobol web searches will use :mod:`eventlet.green.urllib2` instead of the built-in :mod:`urllib2` module. Default: ``False``.

Templates
---------

For convenience, :mod:`.sobol` provides a template at ``sobol/search/_list.html`` which can be used with an ``{% include %}`` tag inside a full search page template to list the search results. The ``_list.html`` template also uses a basic jQuery script (``static/sobol/ajax_search.js``) to handle AJAX search result loading if the AJAX API of the current :class:`.SearchView` is enabled. If you want to use ``_list.html``, but want to provide your own version of jQuery or your own AJAX loading script, or if you want to include the basic script somewhere else (like inside the ``<head>``) simply do the following::

	{% include "sobol/search/_list.html" with suppress_scripts=1 %}

"""

from philo.contrib.sobol.search import *