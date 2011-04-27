from django.http import HttpResponse
from django.utils.feedgenerator import SyndicationFeed
import vobject


# Map the keys in the ICalendarFeed internal dictionary to the names of iCalendar attributes.
FEED_ICAL_MAP = {
	'title': 'x-wr-calname',
	'description': 'x-wr-caldesc',
	#'link': ???,
	#'language': ???,
	#author_email
	#author_name
	#author_link
	#subtitle
	#categories
	#feed_url
	#feed_copyright
	'id': 'prodid',
	'ttl': 'x-published-ttl'
}


ITEM_ICAL_MAP = {
	'title': 'summary',
	'description': 'description',
	'link': 'url',
	# author_email, author_name, and author_link need special handling. Consider them the
	# 'organizer' of the event <http://tools.ietf.org/html/rfc5545#section-3.8.4.3> and
	# construct something based on that.
	'pubdate': 'created',
	'last_modified': 'last-modified',
	#'comments' require special handling as well <http://tools.ietf.org/html/rfc5545#section-3.8.1.4>
	'unique_id': 'uid',
	'enclosure': 'attach', # does this need special handling?
	'categories': 'categories', # does this need special handling?
	# ttl is ignored.
	'start': 'dtstart',
	'end': 'dtend',
}


class ICalendarFeed(SyndicationFeed):
	mime_type = 'text/calendar'
	
	def add_item(self, *args, **kwargs):
		for kwarg in ['start', 'end', 'last_modified', 'location']:
			kwargs.setdefault(kwarg, None)
		super(ICalendarFeed, self).add_item(*args, **kwargs)
	
	def write(self, outfile, encoding):
		# TODO: Use encoding... how? Just convert all values when setting them should work...
		cal = vobject.iCalendar()
		
		# IE/Outlook needs this. See
		# <http://blog.thescoop.org/archives/2007/07/31/django-ical-and-vobject/>
		cal.add('method').value = 'PUBLISH'
		
		for key, val in self.feed.items():
			if key in FEED_ICAL_MAP and val:
				cal.add(FEED_ICAL_MAP[key]).value = val
		
		for item in self.items:
			# TODO: handle multiple types of events.
			event = cal.add('vevent')
			for key, val in item.items():
				#TODO: handle the non-standard items like comments and author.
				if key in ITEM_ICAL_MAP and val:
					event.add(ITEM_ICAL_MAP[key]).value = val
		
		cal.serialize(outfile)
		
		# Some special handling for HttpResponses. See link above.
		if isinstance(outfile, HttpResponse):
			filename = self.feed.get('filename', 'filename.ics')
			outfile['Filename'] = filename
			outfile['Content-Disposition'] = 'attachment; filename=%s' % filename