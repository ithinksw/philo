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

   .. attribute:: status_code

      An :class:`IntegerField` which uses :attr:`STATUS_CODES` as its choices. Determines whether the redirect is considered temporary or permanent.

   .. attribute:: target_node

      An optional :class:`ForeignKey` to a :class:`Node`. If provided, that node will be used as the basis for the redirect.

   .. attribute:: url_or_subpath

      A :class:`CharField` which may contain an absolute or relative URL. This will be validated with :class:`philo.validators.RedirectValidator`.

   .. attribute:: reversing_parameters

      A :class:`~philo.models.fields.JSONField` instance. If the value of :attr:`reversing_parameters` is not None, the :attr:`url_or_subpath` will be treated as the name of a view to be reversed. The value of :attr:`reversing_parameters` will be passed into the reversal as args if it is a list or as kwargs if it is a dictionary.

   .. attribute:: target_url

      Calculates and returns the target url based on the :attr:`target_node`, :attr:`url_or_subpath`, and :attr:`reversing_parameters`.

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