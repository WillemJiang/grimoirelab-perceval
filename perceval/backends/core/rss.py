# -*- coding: utf-8 -*-
#
# Copyright (C) 2016 Bitergia
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
#
# Authors:
#     Alvaro del Castillo <acs@bitergia.com>
#

import json
import logging

import feedparser
import requests

from ...backend import (Backend,
                        BackendCommand,
                        BackendCommandArgumentParser,
                        metadata)
from ...errors import CacheError
from ...utils import (DEFAULT_DATETIME,
                      datetime_to_utc,
                      str_to_datetime,
                      urljoin)


logger = logging.getLogger(__name__)


class RSS(Backend):
    """RSS backend for Perceval.

    This class retrieves the entries from a RSS feed.
    To initialize this class the URL must be provided.
    The `url` will be set as the origin of the data.

    :param url: RSS url
    :param tag: label used to mark the data
    :param cache: cache object to store raw data
    """
    version = '0.1.0'

    def __init__(self, url, tag=None, cache=None):
        origin = url

        super().__init__(origin, tag=tag, cache=cache)
        self.url = url
        self.client = RSSClient(url)

    @metadata
    def fetch(self):
        """Fetch the entries from the url.

        The method retrieves all entries from a RSS url

        :returns: a generator of entries
        """

        logger.info("Looking for rss entries at feed '%s'", self.url)

        self._purge_cache_queue()
        nentries = 0  # number of entries

        raw_entries = self.client.get_entries()
        self._push_cache_queue(raw_entries)
        entries = self.parse_feed(raw_entries)['entries']
        self._flush_cache_queue()
        for item in entries:
            yield item
            nentries += 1

        logger.info("Total number of entries: %i", nentries)

    @classmethod
    def parse_feed(self, raw_entries):
        return feedparser.parse(raw_entries)

    @metadata
    def fetch_from_cache(self):
        """Fetch the entries from the cache.

        :returns: a generator of entries

        :raises CacheError: raised when an error occurs accessing the
            cache
        """
        if not self.cache:
            raise CacheError(cause="cache instance was not provided")

        cache_entries = next(self.cache.retrieve())
        entries = feedparser.parse(cache_entries)['entries']

        for item in entries:
            yield item

    @classmethod
    def has_caching(cls):
        """Returns whether it supports caching entries on the fetch process.

        :returns: this backend supports entries cache
        """
        return True

    @classmethod
    def has_resuming(cls):
        """Returns whether it supports to resume the fetch process.

        :returns: this backend does not supports entries resuming
        """
        return False

    @staticmethod
    def metadata_id(item):
        """Extracts the identifier from an entry item."""
        return str(item['link'])

    @staticmethod
    def metadata_updated_on(item):
        """Extracts the update time from a RSS item.

        The timestamp is extracted from 'published' field.
        This date is a datetime string that needs to be converted to
        a UNIX timestamp float value.

        :param item: item generated by the backend

        :returns: a UNIX timestamp
        """
        ts = str_to_datetime(item['published'])

        return ts.timestamp()

    @staticmethod
    def metadata_category(item):
        """Extracts the category from a RSS item.

        This backend only generates one type of item which is
        'entry'.
        """
        return 'entry'


class RSSClient:
    """RSS API client.

    This class implements a simple client to retrieve entries from
    projects in a RSS node.

    :param url: URL of rss node: https://item.opnfv.org/ci

    :raises HTTPError: when an error occurs doing the request
    """

    def __init__(self, url):
        self.url = url

    def get_entries(self):
        """ Retrieve all entries from a RSS feed"""

        req = requests.get(self.url)
        req.raise_for_status()
        return req.text


class RSSCommand(BackendCommand):
    """Class to run RSS backend from the command line."""

    BACKEND = RSS

    @staticmethod
    def setup_cmd_parser():
        """Returns the RSS argument parser."""

        parser = BackendCommandArgumentParser(cache=True)

        # Required arguments
        parser.parser.add_argument('url',
                                   help="URL of the RSS feed")

        return parser
