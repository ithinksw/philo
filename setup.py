#!/usr/bin/env python

from setuptools import setup
import os


# Shamelessly cribbed from django's setup.py file.
def fullsplit(path, result=None):
	"""
	Split a pathname into components (the opposite of os.path.join) in a
	platform-neutral way.
	"""
	if result is None:
		result = []
	head, tail = os.path.split(path)
	if head == '':
		return [tail] + result
	if head == path:
		return result
	return fullsplit(head, [tail] + result)

# Compile the list of packages available, because distutils doesn't have
# an easy way to do this. Shamelessly cribbed from django's setup.py file.
packages, data_files = [], []
root_dir = os.path.dirname(__file__)
if root_dir != '':
    os.chdir(root_dir)
philo_dir = 'philo'

for dirpath, dirnames, filenames in os.walk(philo_dir):
	# Ignore dirnames that start with '.'
	for i, dirname in enumerate(dirnames):
		if dirname.startswith('.'): del dirnames[i]
	if '__init__.py' in filenames:
		packages.append('.'.join(fullsplit(dirpath)))
	elif filenames:
		data_files.append([dirpath, [os.path.join(dirpath, f) for f in filenames]])


version = __import__('philo').VERSION

setup(
	name = 'philo',
	version = '.'.join([str(v) for v in version]),
	url = "http://philocms.org/",
	description = "A foundation for developing web content management systems.",
	long_description = open(os.path.join(root_dir, 'README')).read(),
	maintainer = "iThink Software",
	maintainer_email = "contact@ithinksw.com",
	packages = packages,
	data_files = data_files,
	
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
		'python>=2.5.4',
		'django-mptt>0.4.2,==dev',
	],
	extras_require = {
		'docs': ["sphinx>=1.0"],
		'grappelli': ['django-grappelli>=2.3'],
		'migrations': ['south>=0.7.2'],
		'waldo-recaptcha': ['recaptcha-django'],
		'sobol-eventlet': ['eventlet'],
		'sobol-scrape': ['BeautifulSoup'],
	},
	dependency_links = [
		'https://github.com/django-mptt/django-mptt/tarball/master#egg=django-mptt-dev'
	]
)