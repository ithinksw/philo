from django.core.paginator import Paginator


def paginate(objects, per_page=None, page_number=1):
	"""
	Given a list of objects, return a (page, obj_list) tuple.
	"""
	try:
		per_page = int(per_page)
	except (TypeError, ValueError):
		# Then either it wasn't set or it was set to an invalid value
		return None, objects
	
	# There also shouldn't be pagination if the list is too short. Try count()
	# first - good chance it's a queryset, where count is more efficient.
	try:
		if objects.count() <= per_page:
			return None, objects
	except AttributeError:
		if len(objects) <= per_page:
			return None, objects
	
	paginator = Paginator(objects, per_page)
	try:
		page_number = int(page_number)
	except:
		page_number = 1
	
	# This will raise an EmptyPage error if the page number is out of range.
	# This error is intentionally left for the calling function to handle.
	page = paginator.page(page_number)
	
	return page, page.object_list