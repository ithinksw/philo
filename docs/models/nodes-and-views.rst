Nodes and Views: Building Website structure
===========================================
.. automodule:: philo.models.nodes

Nodes
-----

.. autoclass:: Node
	:show-inheritance:
	:members:

Views
-----

Abstract View Models
++++++++++++++++++++

.. autoclass:: View
	:show-inheritance:
	:members:

.. autoclass:: MultiView
	:show-inheritance:
	:members:

Concrete View Subclasses
++++++++++++++++++++++++

.. autoclass:: Redirect
	:show-inheritance:
	:members:

.. autoclass:: File
	:show-inheritance:
	:members:

Pages
*****

.. automodule:: philo.models.pages

.. autoclass:: Page
	:members:
	:show-inheritance:

.. autoclass:: Template
	:members:
	:show-inheritance:
	
	.. seealso:: :mod:`philo.loaders.database`

.. autoclass:: Contentlet
	:members:

.. autoclass:: ContentReference
	:members: