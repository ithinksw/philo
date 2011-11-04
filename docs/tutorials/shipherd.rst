Using Shipherd in the Admin
===========================

The navigation mechanism is fairly complex; unfortunately, there's no real way around that - without a lot of equally complex code that you are quite welcome to write and contribute! ;-)

For this guide, we'll assume that you have the setup described in :doc:`getting-started`. We'll be adding a main :class:`.Navigation` to the root :class:`.Node` and making it display as part of the :class:`.Template`.

Before getting started, make sure that you've added :mod:`philo.contrib.shipherd` to your :setting:`INSTALLED_APPS`. :mod:`~philo.contrib.shipherd` template tags also require the request context processor, so make sure to set :setting:`TEMPLATE_CONTEXT_PROCESSORS` appropriately::

	TEMPLATE_CONTEXT_PROCESSORS = (
		# Defaults
		"django.contrib.auth.context_processors.auth",
		"django.core.context_processors.debug",
		"django.core.context_processors.i18n",
		"django.core.context_processors.media",
		"django.core.context_processors.static",
		"django.contrib.messages.context_processors.messages"
		...
		"django.core.context_processors.request"
	)

Creating the Navigation
+++++++++++++++++++++++

Start off by adding a new :class:`.Navigation` instance with :attr:`~.Navigation.node` set to the good ole' ``root`` node and :attr:`~.Navigation.key` set to ``main``. The default :attr:`~.Navigation.depth` of 3 is fine.

Now open up that first inline :class:`.NavigationItem`. Make the text ``Hello World`` and set the target :class:`.Node` to, again, ``root``. (Of course, this is a special case. If we had another node that we wanted to point to, we would choose that.)

Press save and you've created your first navigation.

Displaying the Navigation
+++++++++++++++++++++++++

All you need to do now is show the navigation in the template! This is quite easy, using the :ttag:`~philo.contrib.shipherd.templatetags.shipherd.recursenavigation` templatetag. For now we'll keep it simple. Adjust the "Hello World Template" to look like this::
	
	<html>{% load shipherd %}
	    <head>
	        <title>{% container page_title %}</title>
	    </head>
	    <body>
	        <ul>
	            {% recursenavigation node "main" %}
	                <li{% if navloop.active %} class="active"{% endif %}>
	                    <a href="{{ item.get_target_url }}">{{ item.text }}</a>
	                </li>
	            {% endrecursenavigation %}
	        </ul>
	        {% container page_body as content %}
	        {% if content %}
	            <p>{{ content }}</p>
	        {% endif %}
	        <p>The time is {% now %}.</p>
	    </body>
	</html>

Now have a look at the page - your navigation is there!

Linking to google
+++++++++++++++++

Edit the ``main`` :class:`.Navigation` again to add another :class:`.NavigationItem`. This time give it the :attr:`~.NavigationItem.text` ``Google`` and set the :attr:`~.TargetURLModel.url_or_subpath` field to ``http://google.com``. A navigation item will show up on the Hello World page that points to ``google.com``! Granted, your navigation probably shouldn't do that, because confusing navigation is confusing; the point is that it is possible to provide navigation to arbitrary URLs.

:attr:`~.TargetURLModel.url_or_subpath` can also be used in conjuction with a :class:`.Node` to link to a subpath beyond that :class:`.Node`'s url.
