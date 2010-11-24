from django.template import TemplateDoesNotExist
from django.template.loader import BaseLoader
from django.utils.encoding import smart_unicode
from philo.models import Template


class Loader(BaseLoader):
	is_usable=True
	
	def load_template_source(self, template_name, template_dirs=None):
		try:
			template = Template.objects.get_with_path(template_name)
		except Template.DoesNotExist:
			raise TemplateDoesNotExist(template_name)
		return (template.code, smart_unicode(template))