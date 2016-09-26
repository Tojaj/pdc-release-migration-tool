#!/usr/bin/env python
# Copyright (c) 2016 Red Hat
# Licensed under The MIT License (MIT)
# http://opensource.org/licenses/MIT

import copy
import json
import pprint
import operator


class PdcReleaseMigrationTool(object):

    NAME = "PdcReleaseMigrationTool"
    BATCH_SIZE = 100

    def __init__(self, client, logger=None, test=False):
        self.client = client
        self._test = test

        self._releases = []
        self._release_variants = []
        self._content_delivery_repos = []
        self._product_versions = []
        self._products = []
        self._base_products = []

        self._logger = logger

    def _debug(self, msg):
        if self._logger:
            self._logger.debug(msg)

    def _info(self, msg):
        if self._logger:
            self._logger.info(msg)

    def _warning(self, msg):
        if self._logger:
            self._logger.warning(msg)

    def _error(self, msg):
        if self._logger:
            self._logger.error(msg)

    def _filter_existing_items(self, resource, selector, needed_items, query_param=None):
        """Return set of items which are not available on PDC server

        :param query_param: Is tuple ('query_param', [list of values]) or None
        """

        missing_items = set(needed_items)
        available_items = []

        # Get list of items available in PDC
        if not query_param:
            available_items = self.client[resource](page_size=-1)
        else:
            for val in query_param[1]:
                param = {query_param[0]: val}
                t_available_items = self.client[resource](page_size=-1, **param)
                available_items.extend(t_available_items)

        # Remove available items from missing_items set
        for item in available_items:
            if selector(item) in missing_items:
                missing_items.remove(selector(item))

        return missing_items

    def _prepare_post_data(self, resource, items, selector, whitelist, readonlyattrs):
        """Get list of whitelisted items with removed read-only attributes"""

        data = []  # List of items we are about to add

        for item in items:

            # Include only items that are really needed
            if selector(item) not in whitelist:
                continue

            # Debug
            # These messages must be print here, before read-only fields
            # are stripped off
            self._info("%s: Going to add '%s'" % (resource, selector(item)))

            # Remove read-only fields
            item_copy = copy.deepcopy(item)
            for attr in readonlyattrs:
                item_copy.pop(attr, None)

            data.append(item_copy)

        return data

    def _bulk_insert(self, resource, data):
        """Bulk insert of several items at once.

        Items are split into batches by self.BATCH_SIZE num of items.
        """

        for i in range(0, len(data), self.BATCH_SIZE):
            batch = data[i:(i + self.BATCH_SIZE)]

            self._debug("Batch create of '%s':" % resource)
            self._debug(pprint.pformat(batch))

            if self._test:
                continue

            self.client[resource]._(batch)

    def _create_missing_items(self, resource, items, selector, needed_items,
                              readonlyattrs, query_param=None):
        """Create missing items on PDC server"""

        # Debug
        if not needed_items:
            self._debug("%s: No need to add any items" % resource)
            return  # Nothing to do

        missing = self._filter_existing_items(resource, selector, needed_items, query_param)

        # Debug
        for item in (needed_items - missing):
            self._debug("%s: Item '%s' already exists" % (resource, item))

        # No additional items needed
        if not missing:
            self._debug("%s: No need to add any new items" % resource)
            return

        # Add missing items
        data = self._prepare_post_data(resource, items, selector, missing, readonlyattrs)

        if not data:
            return  # Nothing to do

        # Import data into PDC
        self._bulk_insert(resource, data)

    def _get_releases(self, release_ids):
        if not release_ids:
            releases = self.client['releases'](page_size=-1)
            for release in releases:
                if release["release_id"] not in release_ids:
                    continue
                self._releases.append(release)
        else:
            releases = self.client['releases'](release_id=release_ids,
                                               page_size=-1)
            self._releases = releases


    def _post_releases(self, release_ids):
        """Bulk create of releases"""

        # Create missing items in PDC
        self._create_missing_items("releases",
                                   self._releases,
                                   operator.itemgetter("release_id"),
                                   set(release_ids),
                                   ["compose_set", "release_id", "integrated_with"],
                                   query_param=('release_id', release_ids))

    def _get_release_variants(self):
        for release in self._releases:
            variants = self.client['release-variants'](release=release["release_id"],
                                                       page_size=-1)
            self._release_variants.extend(variants)

    def _post_release_variants(self, release_ids):
        """Bulk create of release variants"""

        # Get list of release variants we need to add
        needed_release_variants_ids = set()
        for release_variant in self._release_variants:
            if (release_ids is not None
                    and release_variant["release"] not in release_ids):
                continue
            needed_release_variants_ids.add(
                "%s/%s" % (release_variant["release"], release_variant["uid"]))

        # Create missing items in PDC
        self._create_missing_items("release-variants",
                                   self._release_variants,
                                   lambda x: "%s/%s" % (x["release"], x["uid"]),
                                   needed_release_variants_ids,
                                   [],
                                   query_param=('release', release_ids))

    def _get_content_delivery_repos(self):
        for release in self._releases:
            repos = self.client["content-delivery-repos"](
                release_id=release["release_id"],
                page_size=-1)
            self._content_delivery_repos.extend(repos)

    def _post_content_delivery_repos(self, release_ids):
        """Bulk create of content delivery repos"""

        def repo_selector(repo):
            # Ignore product_id as it's an int
            strrep = "%s:%s:%s:%s:%s:%s:%s:%s:%s" % (
                repo["release_id"],
                repo["name"],
                repo["arch"],
                repo["content_category"],
                repo["content_format"],
                repo["repo_family"],
                repo["service"],
                "1" if repo["shadow"] else "0",
                repo["variant_uid"])
            return strrep

        # Get list of content delivery repos we need to add
        needed_content_delivery_repos = set()
        involved_release_ids = set()
        for repo in self._content_delivery_repos:
            if (release_ids is not None
                    and repo["release_id"] not in release_ids):
                continue
            needed_content_delivery_repos.add(repo_selector(repo))
            involved_release_ids.add(repo["release_id"])

        # Create missing items in PDC
        self._create_missing_items("content-delivery-repos",
                                   self._content_delivery_repos,
                                   repo_selector,
                                   needed_content_delivery_repos,
                                   ["id"],
                                   query_param=('release_id', release_ids))

    def _get_product_versions(self, release_ids):
        product_versions = self.client['product-versions'](page_size=-1)
        for product_version in product_versions:
            for release in product_version.get("releases", []):
                if release in release_ids:
                    self._product_versions.append(product_version)
                    break

    def _post_product_versions(self, release_ids):
        """Bulk create of product versions"""

        # Get list of product versions we need to add
        needed_product_versions_ids = set()
        for release in self._releases:
            if (release_ids is not None
                    and release["release_id"] not in release_ids):
                continue
            if not release.get("product_version"):
                continue
            needed_product_versions_ids.add(release["product_version"])

        # Create missing items in PDC
        self._create_missing_items("product-versions",
                                   self._product_versions,
                                   operator.itemgetter("product_version_id"),
                                   needed_product_versions_ids,
                                   ["active", "product_version_id", "releases"])

    def _get_products(self):
        needed_products = set([pv["product"] for pv in self._product_versions])
        products = self.client["products"](page_size=-1)
        for product in products:
            if product["short"] not in needed_products:
                continue
            self._products.append(product)

    def _post_products(self, release_ids):
        """Bulk create of products"""

        # Get list of products we need to add
        needed_product_shorts = set()
        for release in self._releases:
            if (release_ids is not None
                    and release["release_id"] not in release_ids):
                continue
            if not release.get("product_version"):
                continue
            product_version_id = release.get("product_version")
            for product_version in self._product_versions:
                if product_version["product_version_id"] == product_version_id:
                    needed_product_shorts.add(product_version["product"])
                    break

        # Create missing items in PDC
        self._create_missing_items("products",
                                   self._products,
                                   operator.itemgetter("short"),
                                   needed_product_shorts,
                                   ["active", "product_versions"])

    def _get_base_products(self):
        needed_base_products = set([p["base_product"] for p in self._releases if p.get("base_product")])
        base_products = self.client["base-products"](page_size=-1)
        for base_product in base_products:
            if base_product["base_product_id"] not in needed_base_products:
                continue
            self._base_products.append(base_product)

    def _post_base_products(self, release_ids):
        """Bulk create of base products"""

        # Get list of base_products we need to add
        needed_base_product_ids = set()
        for release in self._releases:
            if (release_ids is not None
                    and release["release_id"] not in release_ids):
                continue
            if not release.get("base_product"):
                continue
            needed_base_product_ids.add(release["base_product"])

        # Create missing items in PDC
        self._create_missing_items("base-products",
                                   self._base_products,
                                   operator.itemgetter("base_product_id"),
                                   needed_base_product_ids,
                                   ["base_product_id"])

    def dump(self, f, release_ids):
        self._get_releases(release_ids)
        self._get_release_variants()
        self._get_content_delivery_repos()
        self._get_product_versions(release_ids)
        self._get_products()
        self._get_base_products()

        ret = [{
            "name": self.NAME,
            "version": 1,
        }, {
            "releases": self._releases,
            "release-variants": self._release_variants,
            "content-delivery-repos": self._content_delivery_repos,
            "product-versions": self._product_versions,
            "products": self._products,
            "base-products": self._base_products,
        }]

        json.dump(ret, f, indent=2, separators=(',', ': '), sort_keys=True)

        return True

    def load(self, f, release_ids):
        try:
            data = json.load(f)
        except ValueError as err:
            self._error("Bad input file format: %s" % err)
            return False

        # Check input data format
        if (not isinstance(data, list)
                or len(data) != 2
                or not isinstance(data[0], dict)
                or not isinstance(data[1], dict)):
            self._error("Bad input file format")
            return False

        header, data = data

        # Check header
        if header.get("name") != self.NAME:
            self._warning("Bad format name '%s'" % header.get("name"))

        # Parse data
        self._releases = data.get("releases")
        self._release_variants = data.get("release-variants")
        self._content_delivery_repos = data.get("content-delivery-repos")
        self._product_versions = data.get("product-versions")
        self._products = data.get("products")
        self._base_products = data.get("base-products")

        # Sanity check of the data
        if not self._releases:
            self._warning("Migration data doesn't contain any releases")
            return False

        # Get list of releases we are going to add
        if not release_ids:
            release_ids = [release["release_id"] for release in self._releases]

        # Load data into PDC
        self._post_base_products(release_ids)
        self._post_products(release_ids)
        self._post_product_versions(release_ids)
        self._post_releases(release_ids)
        self._post_release_variants(release_ids)
        self._post_content_delivery_repos(release_ids)

        return True
