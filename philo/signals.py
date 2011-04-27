from django.dispatch import Signal


entity_class_prepared = Signal(providing_args=['class'])
view_about_to_render = Signal(providing_args=['request', 'extra_context'])
view_finished_rendering = Signal(providing_args=['response'])
page_about_to_render_to_string = Signal(providing_args=['request', 'extra_context'])
page_finished_rendering_to_string = Signal(providing_args=['string'])