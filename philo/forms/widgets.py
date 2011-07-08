from django.forms.widgets import Textarea
from django.utils import simplejson as json

__all__ = ('EmbedWidget',)

class EmbedWidget(Textarea):
	"""A form widget with the HTML class embedding and an embedded list of content-types."""
	def __init__(self, attrs=None):
		from philo.models import value_content_type_limiter
		
		content_types = value_content_type_limiter.classes
		data = []
		
		for content_type in content_types:
			data.append({'app_label': content_type._meta.app_label, 'object_name': content_type._meta.object_name.lower(), 'verbose_name': unicode(content_type._meta.verbose_name)})
		
		json_ = json.dumps(data)
		
		default_attrs = {'class': 'embedding vLargeTextField', 'data-content-types': json_ }
		
		if attrs:
			default_attrs.update(attrs)
			
		super(EmbedWidget, self).__init__(default_attrs)
		
	class Media:
		css = {
			'all': ('philo/css/EmbedWidget.css',),
		}
		js = ('philo/js/EmbedWidget.js',)