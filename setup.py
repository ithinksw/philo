#!/usr/bin/env python
import os
from setuptools import setup, find_packages


version = __import__('philo').VERSION


setup(
	name = 'philo',
	version = '.'.join([str(v) for v in version]),
	url = "http://philocms.org/",
	description = "A foundation for developing web content management systems.",
	long_description = open(os.path.join(os.path.dirname(__file__), 'README')).read(),
	maintainer = "iThink Software",
	maintainer_email = "contact@ithinksw.com",
	packages = find_packages(),
	include_package_data=True,
	
	classifiers = [
		'Environment :: Web Environment',
		'Framework :: Django',
		'Intended Audience :: Developers',
		'License :: OSI Approved :: ISC License (ISCL)',
		'Operating System :: OS Independent',
		'Programming Language :: Python',
		'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
		'Topic :: Software Development :: Libraries :: Application Frameworks',
	],
	platforms = ['OS Independent'],
	license = 'ISC License (ISCL)',
	
	install_requires = [
		'django>=1.3',
		'django-mptt>0.4.2,==dev',
	],
	extras_require = {
		'docs': ["sphinx>=1.0"],
		'grappelli': ['django-grappelli>=2.3'],
		'migrations': ['south>=0.7.2'],
		'waldo-recaptcha': ['recaptcha-django'],
		'sobol-eventlet': ['eventlet'],
		'sobol-scrape': ['BeautifulSoup'],
		'penfield': ['django-taggit>=0.9'],
	},
	dependency_links = [
		'https://github.com/django-mptt/django-mptt/tarball/master#egg=django-mptt-dev'
	]
)
