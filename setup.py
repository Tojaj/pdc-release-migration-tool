#!/usr/bin/env python
"""Setup script"""

from setuptools import find_packages, setup

VERSION = '0.0.1'

setup(
    name='pdc-release-migration-tool',
    description='Command line tool for migration/backup of releases from PDC',
    version=VERSION,
    license='MIT',
    url='https://github.com/Tojaj/pdc-release-migration-tool',
    download_url='https://github.com/Tojaj/pdc-release-migration-tool/releases',
    author='Tomas Mlcoch',
    author_email='tmlcoch@redhat.com',

    install_requires=['pdc-client'],
    packages=find_packages(exclude=["tests"]),
    scripts=["bin/pdc-release-migration-tool"],

    tests_require=['mock'],
    test_suite='tests',

    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: MIT License',
        'Topic :: Utilities'
    ]
)
