from django import template
from django.conf import settings


register = template.Library()


class MembersofNode(template.Node):
	def __init__(self, collection, model, as_var):
		self.collection = template.Variable(collection)
		self.model = template.Variable(model)
		self.as_var = as_var
		
	def render(self, context):
		try:
			collection = self.collection.resolve(context)
			model = self.model.resolve(context)
			context[self.as_var] = collection.members.with_model(model)
		except:
			pass
		return settings.TEMPLATE_STRING_IF_INVALID
	
	
def do_membersof(parser, token):
	"""
	{% membersof <collection> with <model> as <var> %}
	"""
	params=token.split_contents()
	tag = params[0]
	
	if len(params) < 6:
		raise template.TemplateSyntaxError('"%s" template tag requires six parameters' % tag)
		
	if params[2] != 'with':
		raise template.TemplateSyntaxError('"%s" template tag requires the third parameter to be "with"' % tag)
		
	if params[4] != 'as':
		raise template.TemplateSyntaxError('"%s" template tag requires the fifth parameter to be "as"' % tag)
	
	return MembersofNode(collection=params[1], model=params[3], as_var=params[5])


register.tag('membersof', do_membersof)