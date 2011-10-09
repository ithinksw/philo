class HttpNotAcceptable(Exception):
	"""This will be raised in :meth:`.FeedView.get_feed_type` if an Http-Accept header will not accept any of the feed content types that are available."""
	pass