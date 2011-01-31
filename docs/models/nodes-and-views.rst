Nodes and Views: Building Website structure
===========================================
.. currentmodule:: philo.models

Nodes
-----

:class:`Node`\ s are the basic building blocks of a website using Philo. They define the URL hierarchy and connect each URL to a :class:`View` subclass instance which is used to generate an HttpResponse.

.. class:: Node

   :class:`!Node` subclasses :class:`TreeEntity`. It defines the following additional methods and attributes:

   .. attribute:: view

      :class:`GenericForeignKey` to a non-abstract subclass of :class:`View`

   .. attribute:: accepts_subpath

      A property shortcut for :attr:`self.view.accepts_subpath <View.accepts_subpath>`

   .. method:: render_to_response(request[, extra_context=None])

      This is a shortcut method for :meth:`View.render_to_response`

   .. method:: get_absolute_url()

      As long as :mod:`philo.urls` is included somewhere in the urlpatterns, this will return the URL of this node. The returned value will always start and end with a slash.

Views
-----

Abstract View Models
++++++++++++++++++++
.. class:: View

   :class:`!View` is an abstract model that represents an item which can be "rendered", either in response to an :class:`HttpRequest` or as a standalone. It subclasses :class:`Entity`, and defines the following additional methods and attributes:

   .. attribute:: accepts_subpath

      Defines whether this View class can handle subpaths. Default: ``False``

   .. attribute:: nodes

      A generic relation back to nodes.

   .. method:: get_subpath(obj)

      If the view :attr:`accepts subpaths <.accepts_subpath>`, try to find a reversal for the given object using ``self`` as the urlconf. This method calls :meth:`~.get_reverse_params` with ``obj`` as the argument to find out the reversing parameters for that object.

   .. method:: get_reverse_params(obj)

      This method should return a ``view_name``, ``args``, ``kwargs`` tuple suitable for reversing a url for the given ``obj`` using ``self`` as the urlconf.

   .. method:: attributes_with_node(node)

      Returns a :class:`QuerySetMapper` using the :class:`node <Node>`'s attributes as a passthrough.

   .. method:: render_to_response(request[, extra_context=None])

      Renders the :class:`View` as an :class:`HttpResponse`. This will raise :const:`philo.exceptions.MIDDLEWARE_NOT_CONFIGURED` if the `request` doesn't have an attached :class:`Node`. This can happen if :class:`philo.middleware.RequestNodeMiddleware` is not in :setting:`settings.MIDDLEWARE_CLASSES` or if it is not functioning correctly.

      :meth:`!render_to_response` will send the :obj:`view_about_to_render <philo.signals.view_about_to_render>` signal, then call :meth:`actually_render_to_response`, and finally send the :obj:`view_finished_rendering <philo.signals.view_finished_rendering>` signal before returning the ``response``.

   .. method:: actually_render_to_response(request[, extra_context=None])

      Concrete subclasses must override this method to provide the business logic for turning a ``request`` and ``extra_context`` into an :class:`HttpResponse`.

.. class:: MultiView

   :class:`!MultiView` is an abstract model which represents a section of related pages - for example, a :class:`~philo.contrib.penfield.BlogView` might have a foreign key to :class:`Page`\ s for an index, an entry detail, an entry archive by day, and so on. :class:`!MultiView` subclasses :class:`View`, and defines the following additional methods and attributes:

   .. attribute:: accepts_subpath

      Same as :attr:`View.accepts_subpath`. Default: ``True``

   .. attribute:: urlpatterns

      Returns urlpatterns that point to views (generally methods on the class). :class:`!MultiView`\ s can be thought of as "managing" these subpaths.

   .. method:: actually_render_to_response(request[, extra_context=None])

      Resolves the remaining subpath left after finding this :class:`View`'s node using :attr:`self.urlpatterns <urlpatterns>` and renders the view function (or method) found with the appropriate args and kwargs.

   .. method:: get_context()

      Hook for providing instance-specific context - such as the value of a Field - to all views.

   .. method:: basic_view(field_name)

      Given the name of a field on ``self``, accesses the value of that field and treats it as a :class:`View` instance. Creates a basic context based on :meth:`get_context` and any extra_context that was passed in, then calls the :class:`View` instance's :meth:`~View.render_to_response` method. This method is meant to be called to return a view function appropriate for :attr:`urlpatterns`.

Concrete View Subclasses
++++++++++++++++++++++++

.. class:: Redirect

   A :class:`View` subclass. Defines a 301 or 302 redirect to a different url on an absolute or relative path.

   .. attribute:: STATUS_CODES

      A choices tuple of redirect status codes (temporary or permanent).

   .. attribute:: target

      A :class:`CharField` which may contain an absolute or relative URL. This will be validated with :class:`philo.validators.RedirectValidator`.

   .. attribute:: status_code

      An :class:`IntegerField` which uses :attr:`STATUS_CODES` as its choices. Determines whether the redirect is considered temporary or permanent.

   .. method:: actually_render_to_response(request[, extra_context=None])

      Returns an :class:`HttpResponseRedirect` to :attr:`self.target`.

.. class:: File

   A :class:`View` subclass. Stores an arbitrary file.

   .. attribute:: mimetype

      Defines the mimetype of the uploaded file. This will not be validated.

   .. attribute:: file

      Contains the uploaded file. Files are uploaded to ``philo/files/%Y/%m/%d``.

   .. method:: __unicode__()

      Returns the name of :attr:`self.file <file>`.

Pages
*****

:class:`Page`\ s are the most frequently used :class:`View` subclass. They define a basic HTML page and its associated content. Each :class:`Page` renders itself according to a :class:`Template`. The :class:`Template` may contain :ttag:`container` tags, which define related :class:`Contentlet`\ s and :class:`ContentReference`\ s for any page using that :class:`Template`.

.. class:: Page

   A :class:`View` subclass. Represents a page - something which is rendered according to a template. The page will have a number of related Contentlets depending on the template selected - but these will appear only after the page has been saved with that template.

   .. attribute:: template

      A :class:`ForeignKey` to the :class:`Template` used to render this :class:`Page`.

   .. attribute:: title

      The name of this page. Chances are this will be used for organization - i.e. finding the page in a list of pages - rather than for display.

   .. attribute:: containers

      Returns :attr:`self.template.containers <Template.containers>` - a tuple containing the specs of all :ttag:`container`\ s defined in the :class:`Template`. The value will be cached on the instance so that multiple accesses will be less expensive.

   .. method:: render_to_string([request=None, extra_context=None])

      In addition to rendering as an :class:`HttpResponse`, a :class:`Page` can also render as a string. This means, for example, that :class:`Page`\ s can be used to render emails or other non-HTML-related content with the same :ttag:`container`-based functionality as is used for HTML.

   .. method:: actually_render_to_response(request[, extra_context=None])

      Returns an :class:`HttpResponse` with the content of the :meth:`render_to_string` method and the mimetype set to :attr:`self.template.mimetype <Template.mimetype>`.

   .. clean_fields(self[, exclude=None)

      This is an override of the default model clean_fields method. Essentially, in addition to validating the fields, this method validates the :class:`Template` instance that is used to render this :class:`Page`. This is useful for catching template errors before they show up as 500 errors on a live site.

   .. method:: __unicode__()

      Returns :meth:`self.title <title>`

.. class:: Template

   Subclasses :class:`TreeModel`. Represents a database-driven django template. Defines the following additional methods and attributes:

   .. attribute:: name

      The name of the template. Used for organization and debugging.

   .. attribute:: documentation

      Can be used to let users know what the template is meant to be used for.

   .. attribute:: mimetype

      Defines the mimetype of the template. This is not validated. Default: ``text/html``.

   .. attribute:: code

      An insecure :class:`~philo.models.fields.TemplateField` containing the django template code for this template.

   .. attribute:: containers

      Returns a tuple where the first item is a list of names of contentlets referenced by containers, and the second item is a list of tuples of names and contenttypes of contentreferences referenced by containers. This will break if there is a recursive extends or includes in the template code. Due to the use of an empty Context, any extends or include tags with dynamic arguments probably won't work.

   .. method:: __unicode__()

      Returns the results of the :meth:`~TreeModel.get_path` method, using the "name" field and a chevron joiner.

.. class:: Contentlet

   Defines a piece of content on a page. This content is treated as a secure :class:`~philo.models.fields.TemplateField`.

   .. attribute:: page

      The page which this :class:`Contentlet` is related to.

   .. attribute:: name

      This represents the name of the container as defined by a :ttag:`container` tag.

   .. attribute:: content

      A secure :class:`~philo.models.fields.TemplateField` holding the content for this :class:`Contentlet`. Note that actually using this field as a template requires use of the :ttag:`include_string` template tag.

   .. method:: __unicode__()

      Returns :attr:`self.name <name>`

.. class:: ContentReference

   Defines a model instance related to a page.

   .. attribute:: page

      The page which this :class:`ContentReference` is related to.

   .. attribute:: name

      This represents the name of the container as defined by a :ttag:`container` tag.

   .. attribute:: content

      A :class:`GenericForeignKey` to a model instance. The content type of this instance is defined by the :ttag:`container` tag which defines this :class:`ContentReference`.

   .. method:: __unicode__()

      Returns :attr:`self.name <name>`