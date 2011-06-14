Getting started with philo
==========================

.. note:: This guide assumes that you have worked with Django's built-in administrative interface.

Once you've installed `philo`_ and `mptt`_ to your python path, there are only a few things that you need to do to get :mod:`philo` working.

1. Add :mod:`philo` and :mod:`mptt` to :setting:`settings.INSTALLED_APPS`::
		
	INSTALLED_APPS = (
		...
		'philo',
		'mptt',
		...
	)

2. Syncdb or run migrations to set up your database.
	
3. Add :class:`philo.middleware.RequestNodeMiddleware` to :setting:`settings.MIDDLEWARE_CLASSES`::
	
	MIDDLEWARE_CLASSES = (
		...
		'philo.middleware.RequestNodeMiddleware',
		...
	)
	
4. Include :mod:`philo.urls` somewhere in your urls.py file. For example::
	
	from django.conf.urls.defaults import patterns, include, url
	urlpatterns = patterns('',
		url(r'^', include('philo.urls')),
	)

Philo should be ready to go! (Almost.)

.. _philo: http://philocms.org/
.. _mptt: http://github.com/django-mptt/django-mptt

Hello world
+++++++++++

Now that you've got everything configured, it's time to set up your first page! Easy peasy. Open up the admin and add a new :class:`.Template`. Call it "Hello World Template". The code can be something like this::
	
	<html>
		<head>
			<title>Hello world!</title>
		</head>
		<body>
			<p>Hello world!</p>
			<p>The time is {% now %}.</p>
		</body>
	</html>

Next, add a philo :class:`.Page` - let's call it "Hello World Page" and use the template you just made.

Now make a philo :class:`.Node`. Give it the slug ``hello-world``. Set the ``view_content_type`` to "Page" and the ``view_object_id`` to the id of the page that you just made - probably 1. If you navigate to ``/hello-world``, you will see the results of rendering the page!

Setting the root node
+++++++++++++++++++++

So what's at ``/``? If you try to load it, you'll get a 404 error. This is because there's no :class:`.Node` located there - and since :attr:`.Node.slug` is a required field, getting a node there is not as simple as leaving the :attr:`.~Node.slug` blank.

In :mod:`philo`, the node that is displayed at ``/`` is called the "root node" of the current :class:`Site`. To represent this idea cleanly in the database, :mod:`philo` adds a :class:`ForeignKey` to :class:`.Node` to the :class:`django.contrib.sites.models.Site` model.

Since there's only one :class:`.Node` in your :class:`Site`, we probably want ``hello-world`` to be the root node. All you have to do is edit the current :class:`Site` and set its root node to ``hello-world``. Now you can see the page rendered at ``/``!

Editing page contents
+++++++++++++++++++++

Great! We've got a page that says "Hello World". But what if we want it to say something else? Should we really have to edit the :class:`.Template` to change the content of the :class:`.Page`? And what if we want to share the :class:`.Template` but have different content? Adjust the :class:`.Template` to look like this::
	
	<html>
	    <head>
	        <title>{% container page_title %}</title>
	    </head>
	    <body>
	        {% container page_body as content %}
	        {% if content %}
	            <p>{{ content }}</p>
	        {% endif %}
	        <p>The time is {% now "jS F Y H:i" %}.</p>
	    </body>
	</html>

Now go edit your :class:`.Page`. Two new fields called "Page title" and "Page body" have shown up! You can put anything you like in here and have it show up in the appropriate places when the page is rendered.

.. seealso:: :ttag:`philo.templatetags.containers.container`

Congrats! You've done it!
