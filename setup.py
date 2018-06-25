import os
from setuptools import setup, find_packages

pname = 'remotelogin'

cur_dir = os.path.abspath(os.path.dirname(__file__))

# extract information from __version__.py
info = {}
with open(os.path.join(cur_dir, pname, '__version__.py')) as f:
    exec(f.read(), info)

# long description from README.md
try:
    long_description = open('README.md', 'rt').read()
except IOError:
    long_description = ''

requires = ['pyyaml',
            'paramiko',
            'scp',
            'cryptography',
            'sqlalchemy']

package_data={'': ['MANIFEST.in','README.md'],
              'remotelogin': ['known_ports.csv', 'sample_settings.yaml'],
              'remotelogin.oper_sys.busybox': ['base64.sh'],
              'remotelogin.connections': ['service-names-port-numbers.csv']
}


setup(
    name=pname,
    version=info['__version__'],
    packages=find_packages(exclude=()),
    url=info['__url__'],
    license=['__license__'],
    author=info['__author__'],
    author_email=info['__email__'],
    description=info['__description__'],
    long_description=long_description,
    python_requires=">=3.4",
    install_requires=requires,
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Operating System :: OS Independent',
        'Intended Audience :: Automation',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ],
    include_package_data=True,
    package_data=package_data
)
