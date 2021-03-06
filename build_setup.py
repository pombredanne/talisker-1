import collections
from setuptools.config import read_configuration

config = read_configuration('setup.cfg')
data = {}
collections.OrderedDict()
data.update(config['metadata'])
data.update(config['options'])
data['long_description'] = 'DESCRIPTION'

long_description = open('README.rst').read().strip()
sorted_data = collections.OrderedDict((k, data[k]) for k in sorted(data))


def print_line(k, v, indent='    '):
    if isinstance(v, list):
        print('{}{}=['.format(indent, k))
        for i in v:
            print("{}    '{}',".format(indent, i))
        print('{}],'.format(indent))
    elif isinstance(v, dict):
        print('{}{}=dict('.format(indent, k))
        for k2 in sorted(v):
            print_line(k2, v[k2], indent + '    ')
        print('{}),'.format(indent))
    elif isinstance(v, bool):
        print("{}{}={},".format(indent, k, v))
    elif k == 'long_description':
        print("{}{}={},".format(indent, k, v))
    else:
        print("{}{}='{}',".format(indent, k, v))


print("""#!/usr/bin/env python
#
# Note: this file is autogenerated from setup.cfg for older setuptools
#
try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

DESCRIPTION = '''
{}
'''

setup(""".format(long_description))

for k, v in sorted_data.items():
    print_line(k, v)

print(')')
