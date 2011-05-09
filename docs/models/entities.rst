Entities and Attributes
=======================

.. module:: philo.models.base

One of the core concepts in Philo is the relationship between the :class:`Entity` and :class:`Attribute` classes. :class:`Attribute`\ s represent an arbitrary key/value pair by having one :class:`GenericForeignKey` to an :class:`Entity` and another to an :class:`AttributeValue`.


Attributes
----------

.. autoclass:: Attribute
	:members:

.. autoclass:: AttributeValue
	:members:

.. automodule:: philo.models.base
	:members: attribute_value_limiter

.. autoclass:: JSONValue
	:show-inheritance:

.. autoclass:: ForeignKeyValue
	:show-inheritance:

.. autoclass:: ManyToManyValue
	:show-inheritance:

.. automodule:: philo.models.base
	:members: value_content_type_limiter

.. autofunction:: register_value_model(model)
.. autofunction:: unregister_value_model(model)

Entities
--------

.. autoclass:: Entity
	:members:
	:exclude-members: attribute_set

.. autoclass:: TreeManager
	:members:

.. autoclass:: TreeEntity
	:show-inheritance:
	:members:
	:exclude-members: attribute_set

	.. attribute:: objects

		An instance of :class:`TreeManager`.
	
	.. automethod:: get_path