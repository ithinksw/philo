Nodes and Views: Building Website structure
===========================================
.. automodule:: philo.models.nodes

Nodes
-----

.. autoclass:: Node
	:show-inheritance:
	:members:
	:exclude-members: attribute_set

Views
-----

Abstract View Models
++++++++++++++++++++

.. autoclass:: View
	:show-inheritance:
	:members:
	:exclude-members: attribute_set

.. autoclass:: MultiView
	:show-inheritance:
	:members:
	:exclude-members: attribute_set

Concrete View Subclasses
++++++++++++++++++++++++

.. autoclass:: Redirect
	:show-inheritance:
	:members:
	:exclude-members: attribute_set

.. autoclass:: File
	:show-inheritance:
	:members:
	:exclude-members: attribute_set

Pages
*****

.. automodule:: philo.models.pages

.. autoclass:: Page
	:members:
	:exclude-members: attribute_set
	:show-inheritance:

.. autoclass:: Template
	:members:
	:show-inheritance:
	
	.. seealso:: :mod:`philo.loaders.database`

.. autoclass:: Contentlet
	:members:

.. autoclass:: ContentReference
	:members: