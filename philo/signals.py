from django.dispatch import Signal


#: Sent whenever an Entity subclass has been "prepared" -- that is, after the processing necessary to make :mod:`.AttributeProxyField`\ s work has been completed. This will fire after :obj:`django.db.models.signals.class_prepared`.
#:
#: Arguments that are sent with this signal:
#: 
#: ``sender``
#: 	The model class.
entity_class_prepared = Signal(providing_args=['class'])

#: Sent when a :class:`~philo.models.nodes.View` instance is about to render. This allows you, for example, to modify the ``extra_context`` dictionary used in rendering.
#:
#: Arguments that are sent with this signal:
#:
#: ``sender``
#: 	The :class:`~philo.models.nodes.View` instance
#:
#: ``request``
#: 	The :class:`HttpRequest` instance which the :class:`~philo.models.nodes.View` is rendering in response to.
#:
#: ``extra_context``
#: 	A dictionary which will be passed into :meth:`~philo.models.nodes.View.actually_render_to_response`.
view_about_to_render = Signal(providing_args=['request', 'extra_context'])

#: Sent when a view instance has finished rendering.
#:
#: Arguments that are sent with this signal:
#:
#: ``sender``
#: 	The :class:`~philo.models.nodes.View` instance
#:
#: ``response``
#: 	The :class:`HttpResponse` instance which :class:`~philo.models.nodes.View` view has rendered to.
view_finished_rendering = Signal(providing_args=['response'])

#: Sent when a :class:`~philo.models.pages.Page` instance is about to render as a string. If the :class:`~philo.models.pages.Page` is rendering as a response, this signal is sent after :obj:`view_about_to_render` and serves a similar function. However, there are situations where a :class:`~philo.models.pages.Page` may be rendered as a string without being rendered as a response afterwards.
#:
#: Arguments that are sent with this signal:
#:
#: ``sender``
#: 	The :class:`~philo.models.pages.Page` instance
#:
#: ``request``
#: 	The :class:`HttpRequest` instance which the :class:`~philo.models.pages.Page` is rendering in response to (if any).
#:
#: ``extra_context``
#: 	A dictionary which will be passed into the :class:`Template` context.
page_about_to_render_to_string = Signal(providing_args=['request', 'extra_context'])

#: Sent when a :class:`~philo.models.pages.Page` instance has just finished rendering as a string. If the :class:`~philo.models.pages.Page` is rendering as a response, this signal is sent before :obj:`view_finished_rendering` and serves a similar function. However, there are situations where a :class:`~philo.models.pages.Page` may be rendered as a string without being rendered as a response afterwards.
#:
#: Arguments that are sent with this signal:
#:
#: ``sender``
#: 	The :class:`~philo.models.pages.Page` instance
#:
#: ``string``
#: 	The string which the :class:`~philo.models.pages.Page` has rendered to.
page_finished_rendering_to_string = Signal(providing_args=['string'])