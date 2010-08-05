from django.core.paginator import Paginator


class PaginationProxy(object):
	def __init__(self, paginator=None, page=None, objects=None):
		self.paginator = paginator
		self.page = page
		self.objects = objects
	
	@property
	def page_range(self):
		if not self.paginator:
			return None
		
		return self.paginator.page_range
	
	@property
	def num_pages(self):
		if not self.paginator:
			return None
		
		return self.paginator.num_pages
	
	@property
	def page_number(self):
		if not self.page:
			return None
		
		return self.page.number
	
	def __bool__(self):
		return bool(self.paginator)


def paginate(objects, per_page=None, page_number=1):
	"""
	Given a list of objects, return a (page, obj_list) tuple.
	"""
	try:
		per_page = int(per_page)
	except (TypeError, ValueError):
		# Then either it wasn't set or it was set to an invalid value
		return PaginationProxy(objects=objects)
	
	# There also shouldn't be pagination if the list is too short. Try count()
	# first - good chance it's a queryset, where count is more efficient.
	try:
		if objects.count() <= per_page:
			return PaginationProxy(objects=objects)
	except AttributeError:
		if len(objects) <= per_page:
			return PaginationProxy(objects=objects)
	
	paginator = Paginator(objects, per_page)
	try:
		page_number = int(page_number)
	except:
		page_number = 1
	
	try:
		page = paginator.page(page_number)
	except EmptyPage:
		page = None
	
	return PaginationProxy(paginator, page, objects)