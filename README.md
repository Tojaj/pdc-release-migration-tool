# Tool for migration/backup of PDC releases

[![Build Status](https://travis-ci.org/Tojaj/pdc-release-migration-tool.svg?branch=master)](https://travis-ci.org/Tojaj/pdc-release-migration-tool)
[![Coverage Status](https://coveralls.io/repos/github/Tojaj/pdc-release-migration-tool/badge.svg?branch=master)](https://coveralls.io/github/Tojaj/pdc-release-migration-tool?branch=master)

Command line tool for migration/backup of releases from PDC.

This tool can dump specified releases and their related objects into
a single JSON file and load this file back into PDC.

Objects which are dumped/loaded:

* Base products
* Products
* Product versions
* Releases
* Release variants
* Content delivery repos

During loading, migration tool checks if objects exist by their primary key
and skip the existing ones. Skipped objects are not even updated.
(For example: If you have different description of products in testing
instance then in prod, you don't have to worry, products in prod won't
be overridden).

**Note:** ``release.integrated_with`` is not supported yet and this field
is omitted during load.


## Usage


### Dump

    pdc-release-migration-tool --pdc-server http://test-pdc-instance.com/rest_api/v1/ --dump --output releases.json foo-1.1 foo-1.2


### Load

#### Load all releases available in the file

    pdc-release-migration-tool --pdc-server http://test-pdc-instance.com/rest_api/v1/ --load releases.json

#### Load specific release(s)

    pdc-release-migration-tool --pdc-server http://test-pdc-instance.com/rest_api/v1/ --load releases.json foo-1.2


### Command line options

* ``--test`` - Prints what would be done but doesn't do anything (dry run).
  Useful with ``--verbose``. Works only with ``--load``.
* ``--verbose`` - Verbose output
* ``--develop`` - Develop mode where auth is disabled (use with testing
  instances which don't have kerberos auth available).


## Installation


### Dependencies

* ``python``
* ``pdc-client`` - Client for Product Definition Center(PDC) in Python
  (https://github.com/product-definition-center/pdc-client)
