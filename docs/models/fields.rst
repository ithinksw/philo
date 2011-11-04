Custom Fields
=============

.. automodule:: philo.models.fields
	:members:
	:exclude-members: JSONField, SlugMultipleChoiceField
	
	.. autoclass:: JSONField()
		:members:
	
	.. autoclass:: SlugMultipleChoiceField()
		:members:

AttributeProxyFields
--------------------

.. automodule:: philo.models.fields.entities
	:members:
	
	.. autoclass:: AttributeProxyField(attribute_key=None, verbose_name=None, help_text=None, default=NOT_PROVIDED, editable=True, choices=None, *args, **kwargs)
		:members: