"""
The collection template tags are automatically included as builtins if :mod:`philo` is an installed app.

"""

from django import template
from django.conf import settings
from django.contrib.contenttypes.models import ContentType


register = template.Library()


class MembersofNode(template.Node):
	def __init__(self, collection, model, as_var):
		self.collection = template.Variable(collection)
		self.model = model
		self.as_var = as_var
		
	def render(self, context):
		try:
			collection = self.collection.resolve(context)
			context[self.as_var] = collection.members.with_model(self.model)
		except:
			pass
		return ''


@register.tag
def membersof(parser, token):
	"""
	Given a collection and a content type, sets the results of :meth:`collection.members.with_model <.CollectionMemberManager.with_model>` as a variable in the context.
	
	Usage::
	
		{% membersof <collection> with <app_label>.<model_name> as <var> %}
	
	"""
	params=token.split_contents()
	tag = params[0]
	
	if len(params) < 6:
		raise template.TemplateSyntaxError('"%s" template tag requires six parameters' % tag)
		
	if params[2] != 'with':
		raise template.TemplateSyntaxError('"%s" template tag requires the third parameter to be "with"' % tag)
	
	try:
		app_label, model = params[3].strip('"').split('.')
		ct = ContentType.objects.get_by_natural_key(app_label, model)
	except ValueError:
		raise template.TemplateSyntaxError('"%s" template tag option "with" requires an argument of the form app_label.model (see django.contrib.contenttypes)' % tag)
	except ContentType.DoesNotExist:
		raise template.TemplateSyntaxError('"%s" template tag option "with" requires an argument of the form app_label.model which refers to an installed content type (see django.contrib.contenttypes)' % tag)
		
	if params[4] != 'as':
		raise template.TemplateSyntaxError('"%s" template tag requires the fifth parameter to be "as"' % tag)
	
	return MembersofNode(collection=params[1], model=ct.model_class(), as_var=params[5])