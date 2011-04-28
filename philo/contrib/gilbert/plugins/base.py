from ..extdirect import ext_action


@ext_action
class Plugin(object):
	def __init__(self, site):
		self.site = site
	
	@property
	def index_css_urls(self):
		return []
	
	@property
	def index_js_urls(self):
		return []
	
	@property
	def index_extrahead(self):
		return ''
	
	@property
	def icon_names(self):
		return []