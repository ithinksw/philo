from django.dispatch import Signal


entity_class_prepared = Signal(providing_args=['class'])
view_about_to_render = Signal(providing_args=['request', 'extra_context'])
view_finished_rendering = Signal(providing_args=['response'])
page_about_to_render_to_string = Signal(providing_args=['request', 'extra_context'])
page_finished_rendering_to_string = Signal(providing_args=['string'])


def replace_sender_response(sender, response):
	"""Helper function to swap in a new response."""
	def render_to_response(self, *args, **kwargs):
		return response
	sender.actually_render_to_response = render_to_response