Template Tags
=============

.. automodule:: philo.templatetags

Collections
+++++++++++

.. automodule:: philo.templatetags.collections
		
	.. templatetag:: membersof
	
	membersof
	---------
	
	Usage::
	
		{% membersof <collection> with <app_label>.<model_name> as <var> %}


.. automodule:: philo.templatetags.containers

	.. templatetag:: container
	
	container
	---------
	
	Usage::
	
		{% container <name> [[references <app_label>.<model_name>] as <variable>] %}

.. automodule:: philo.templatetags.embed

	.. templatetag:: embed
	
	embed
	-----
	
	The {% embed %} tag can be used in two ways.
	
	To set which template will be used to render a particular model::
	
		{% embed <app_label>.<model_name> with <template> %}
	
	To embed the instance specified by the given parameters in the document with the previously-specified template (any kwargs provided will be passed into the context of the template)::
	
		{% embed (<app_label>.<model_name> <object_pk> || <instance>) [<argname>=<value> ...] %}

.. automodule:: philo.templatetags.include_string

	.. templatetag:: include_string
	
	include_string
	--------------
	
	Include a flat string by interpreting it as a template.
	
	Usage::
	
		{% include_string <template_code> %}

.. automodule:: philo.templatetags.nodes

	.. templatetag:: node_url
	
	node_url
	--------
	
	Usage::
	
		{% node_url [for <node>] [as <var>] %}
		{% node_url with <obj> [for <node>] [as <var>] %}
		{% node_url <view_name> [<arg1> [<arg2> ...] ] [for <node>] [as <var>] %}
		{% node_url <view_name> [<key1>=<value1> [<key2>=<value2> ...] ] [for <node>] [as <var>] %}
