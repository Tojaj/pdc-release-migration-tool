#!/usr/bin/env python
# Copyright (c) 2016 Red Hat
# Licensed under The MIT License (MIT)
# http://opensource.org/licenses/MIT

import os
import sys
import copy
import operator
import unittest

import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pdc_release_migration_tool import PdcReleaseMigrationTool


class TestCasePdcReleaseMigrationTool(unittest.TestCase):

    def setUp(self):
        pass

    def test_logging_without_logger(self):
        """Test logging without logger (no exception should be raised)"""

        rmt = PdcReleaseMigrationTool(None)

        rmt._debug("test _debug")
        rmt._info("test _info")
        rmt._warning("test _warning")
        rmt._error("test _error")

    def test_logging(self):
        """Test logging with logger"""

        mock_logger = mock.Mock()
        rmt = PdcReleaseMigrationTool(None, logger=mock_logger)

        rmt._debug("test _debug")
        mock_logger.debug.assert_called_once_with("test _debug")

        rmt._info("test _info")
        mock_logger.info.assert_called_once_with("test _info")

        rmt._warning("test _warning")
        mock_logger.warning.assert_called_once_with("test _warning")

        rmt._error("test _error")
        mock_logger.error.assert_called_once_with("test _error")

    def test_filter_existing_items(self):
        """Test _filter_existing_items method"""

        # Server mock
        client_mock = mock.MagicMock()
        items = [
            {
                'name': 'Foo',
                'category': 'base',
                'size': 10,
            }
        ]
        client_mock['test-resource'].return_value = items

        # Input parameters
        resource = "test-resource"
        selector = operator.itemgetter("name")
        needed_items = ['Foo', 'Bar']

        # Test
        rmt = PdcReleaseMigrationTool(client_mock)
        data = rmt._filter_existing_items(resource, selector, needed_items)

        # Expected output
        # * Only items from list of needed_items that are not available on
        #   the server (after selector applied) are returned
        expected = set(['Bar'])
        self.assertEqual(data, expected)

    def test_prepare_post_data(self):
        """Test _prepare_post_data method"""

        # Input parameters
        resource = "test-resource"
        items = [
            {
                'name': 'Foo',
                'category': 'base',
                'size': 10,
            }, {
                'name': 'Bar',
                'category': 'child',
                'size': 15,
            }, {
                'name': 'Fuu',
                'category': 'child',
                'size': 20,
            }
        ]
        items_copy = copy.deepcopy(items)
        selector = operator.itemgetter("name")
        whitelist = set(['Foo', 'Fuu'])
        readonlyattrs = ['size']

        # Test
        rmt = PdcReleaseMigrationTool(None)
        data = rmt._prepare_post_data(resource,
                                      items,
                                      selector,
                                      whitelist,
                                      readonlyattrs)

        # Expected output
        # * Only items on whitelist are available
        # * Read only attributes are removed
        expected = [
            {
                'name': 'Foo',
                'category': 'base',
            }, {
                'name': 'Fuu',
                'category': 'child',
            }
        ]
        self.assertEqual(data, expected)

        # Assert that input array is not modified!
        self.assertEqual(items, items_copy)


if __name__ == '__main__':
    unittest.main()
