Nodes and Views: Building Website structure
===========================================
.. currentmodule:: philo.models
.. class:: Node

   .. attribute:: view

      :class:`GenericForeignKey` to a non-abstract subclass of :class:`View`

   .. attribute:: accepts_subpath

      A property shortcut for :attr:`self.view.accepts_subpath <View.accepts_subpath>`

   .. method:: render_to_response(request[, extra_context=None])

      This is a shortcut method for :meth:`View.render_to_response`

   .. method:: get_absolute_url()

      As long as :mod:`philo.urls` is included somewhere in the urlpatterns, this will return the URL of this node. The returned value will always start and end with a slash.

.. class:: View

   :class:`!View` is an abstract model that represents an item which can be "rendered", either in response to an :class:`HttpRequest` or as a standalone.

   .. attribute:: accepts_subpath

      Defines whether this View class can handle subpaths.

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