from django.core.paginator import Paginator, InvalidPage, EmptyPage


def paginate(request, entries, entries_per_page):
	paginator = Paginator(entries, entries_per_page)
	try:
		page_number = int(request.GET.get('page', '1'))
		entries = paginator.page(page_number).object_list
		page = paginator.page(page_number)
	except ValueError:
		page_number = 1
		entries = paginator.page(page_number).object_list
		page = paginator.page(page_number)
	try:
		entries = paginator.page(page_number).object_list
		page = paginator.page(page_number)
	except (EmptyPage, InvalidPage):
		entries = paginator.page(paginator.num_pages).object_list
		page = paginator.page(page_number)
	return page