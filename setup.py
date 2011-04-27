#!/usr/bin/env python

from distutils.core import setup
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
	name = 'Philo',
	version = '%s.%s' % (version[0], version[1]),
	packages = packages,
	data_files = data_files,
)