from django.dispatch import Signal


entity_class_prepared = Signal(providing_args=['class'])
view_about_to_render = Signal(providing_args=['node', 'request', 'path', 'subpath', 'extra_context'])
view_finished_rendering = Signal(providing_args=['response'])