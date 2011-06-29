Shipherd
========

.. automodule:: philo.contrib.shipherd
	:members:
	
	:class:`.Node`\ s are useful for structuring a website; however, they are inherently unsuitable for creating site navigation.
	
	The most glaring problem is that a navigation tree based on :class:`.Node`\ s would have one :class:`.Node` as the root, whereas navigation usually has multiple objects at the top level.
	
	Additionally, navigation needs to have display text that is relevant to the current context; however, :class:`.Node`\ s do not have a field for that, and :class:`.View` subclasses with a name or title field will generally need to use it for database-searchable names.
	
	Finally, :class:`.Node` structures are inherently unordered, while navigation is inherently ordered.
	
	:mod:`~philo.contrib.shipherd` exists to resolve these issues by separating navigation structures from :class:`.Node` structures. It is instead structured around the way that site navigation works in the wild:
	
	* A site may have one or more independent navigation bars (Main navigation, side navigation, etc.)
	* A navigation bar may be shared by sections of the website, or even by the entire site.
	* A navigation bar has a certain depth that it displays to.
	
	The :class:`.Navigation` model supplies these features by attaching itself to a :class:`.Node` via :class:`ForeignKey` and adding a :attr:`navigation` property to :class:`.Node` which provides access to a :class:`.Node` instance's inherited :class:`.Navigation`\ s.
	
	Each entry in the navigation bar is then represented by a :class:`.NavigationItem`, which stores information such as the :attr:`~.NavigationItem.order` and :attr:`~.NavigationItem.text` for the entry. Given an :class:`HttpRequest`, a :class:`.NavigationItem` can also tell whether it :meth:`~.NavigationItem.is_active` or :meth:`~.NavigationItem.has_active_descendants`.
	
	Since the common pattern is to recurse through a navigation tree and render each part similarly, :mod:`~philo.contrib.shipherd` also ships with the :ttag:`~philo.contrib.shipherd.templatetags.shipherd.recursenavigation` template tag.

Models
++++++

.. automodule:: philo.contrib.shipherd.models
	:members: Navigation, NavigationItem, NavigationMapper
	:show-inheritance:

.. autoclass:: NavigationManager
	:members:

Template tags
+++++++++++++

.. automodule:: philo.contrib.shipherd.templatetags.shipherd

.. autotemplatetag:: recursenavigation

.. autotemplatefilter:: has_navigation

.. autotemplatefilter:: navigation_host
