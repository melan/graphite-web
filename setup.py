#!/usr/bin/env python

from __future__ import with_statement

import os
import ConfigParser

from glob import glob
from collections import defaultdict
import platform

try:
    from io import BytesIO
except ImportError:
    from StringIO import StringIO as BytesIO

# Graphite historically has an install prefix set in setup.cfg. Being in a
# configuration file, it's not easy to override it or unset it (for installing
# graphite in a virtualenv for instance).
# The prefix is now set by ``setup.py`` and *unset* if an environment variable
# named ``GRAPHITE_NO_PREFIX`` is present.
# While ``setup.cfg`` doesn't contain the prefix anymore, the *unset* step is
# required for installations from a source tarball because running
# ``python setup.py sdist`` will re-add the prefix to the tarball's
# ``setup.cfg``.
with open('setup.cfg', 'r') as f:
    orig_setup_cfg = f.read()
cf = ConfigParser.ConfigParser()
cf.readfp(BytesIO(orig_setup_cfg), 'setup.cfg')

if os.environ.get('GRAPHITE_NO_PREFIX'):
    cf.remove_section('install')
else:
    try:
        cf.add_section('install')
    except ConfigParser.DuplicateSectionError:
        pass
    cf.set('install', 'prefix', '/opt/graphite')
    cf.set('install', 'install-lib', '%(prefix)s/webapp')

with open('setup.cfg', 'wb') as f:
    cf.write(f)

if os.environ.get('USE_SETUPTOOLS'):
    from setuptools import setup

    setup_kwargs = dict(zip_safe=0)

else:
    from distutils.core import setup

    setup_kwargs = dict()

storage_dirs = []
conf_files = []
examples = []
data_files = []
package_data = {}

if not os.environ.get('GRAPHITE_NO_FOLDERS'):
    for subdir in ('whisper', 'ceres', 'rrd', 'log', 'log/webapp'):
        storage_dirs.append(('storage/%s' % subdir, []))

    webapp_content = [(root,
                       [os.path.join(root, f) for f in files]) for root, dirs, files in os.walk('webapp/content')]
    conf_files = [('conf', glob('conf/*.example'))]
    examples = [('examples', glob('examples/example-*'))]

    data_files = webapp_content + storage_dirs + conf_files + examples

    package_data = {'graphite': ['templates/*', 'local_settings.py.example']}
else:
    conf_path = os.environ.get('GRAPHITE_CONF_PATH', '/etc/graphite-web')

    data_files.append((conf_path,
                       glob('conf/*.conf.example') +
                       glob('webapp/graphite/local_settings.py.example')))

    data_files.append(('/var/log/graphite-web', []))

    data_files.append(('/usr/share/graphite',
                       glob('conf/graphite.wsgi.example')))
    data_files.append(('/usr/share/graphite/examples',
                       glob('examples/example-*')))

    webapp_content = [(os.path.join('/usr/share/graphite', root),
                       [os.path.join(root, f) for f in files]) for root, dirs, files in os.walk('webapp/content')]

    data_files.extend(webapp_content)

    package_data = {'graphite': ['templates/*']}

try:
    setup(
        name='graphite-web',
        version='0.9.10',
        url='http://graphite.readthedocs.org',
        author='Chris Davis',
        author_email='chrismd@gmail.com',
        license='Apache Software License 2.0',
        description='Enterprise scalable realtime graphing',
        package_dir={'': 'webapp'},
        packages=[
            'graphite',
            'graphite.account',
            'graphite.browser',
            'graphite.cli',
            'graphite.composer',
            'graphite.dashboard',
            'graphite.events',
            'graphite.graphlot',
            'graphite.metrics',
            'graphite.render',
            'graphite.version',
            'graphite.whitelist',
        ],
        package_data=package_data,
        scripts=glob('bin/*'),
        data_files=data_files,
        **setup_kwargs
    )
finally:
    with open('setup.cfg', 'w') as f:
        f.write(orig_setup_cfg)
