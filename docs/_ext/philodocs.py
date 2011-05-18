import inspect

from sphinx.addnodes import desc_addname
from sphinx.domains.python import PyModulelevel, PyXRefRole
from sphinx.ext import autodoc


DOMAIN = 'py'


class TemplateTag(PyModulelevel):
	indextemplate = "pair: %s; template tag"
	
	def get_signature_prefix(self, sig):
		return self.objtype + ' '
	
	def handle_signature(self, sig, signode):
		fullname, name_prefix = PyModulelevel.handle_signature(self, sig, signode)
		
		for i, node in enumerate(signode):
			if isinstance(node, desc_addname):
				lib = '.'.join(node[0].split('.')[-2:])
				new_node = desc_addname(lib, lib)
				signode[i] = new_node
		
		return fullname, name_prefix


class TemplateTagDocumenter(autodoc.FunctionDocumenter):
	objtype = 'templatetag'
	domain = DOMAIN
	
	@classmethod
	def can_document_member(cls, member, membername, isattr, parent):
		# Only document explicitly.
		return False
	
	def format_args(self):
		return None

class TemplateFilterDocumenter(autodoc.FunctionDocumenter):
	objtype = 'templatefilter'
	domain = DOMAIN
	
	@classmethod
	def can_document_member(cls, member, membername, isattr, parent):
		# Only document explicitly.
		return False

def setup(app):
	app.add_directive_to_domain(DOMAIN, 'templatetag', TemplateTag)
	app.add_role_to_domain(DOMAIN, 'ttag', PyXRefRole())
	app.add_directive_to_domain(DOMAIN, 'templatefilter', TemplateTag)
	app.add_role_to_domain(DOMAIN, 'tfilter', PyXRefRole())
	app.add_autodocumenter(TemplateTagDocumenter)
	app.add_autodocumenter(TemplateFilterDocumenter)