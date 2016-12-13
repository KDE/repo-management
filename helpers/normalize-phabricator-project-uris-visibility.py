#!/usr/bin/env python
# -*- coding: utf-8 -*-

#   Copyright 2016 Luigi Toscano <luigi.toscano@tiscali.it>
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License, under
#   version 2 of the License, or (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details
#
#   You should have received a copy of the GNU General Public
#   License along with this program; if not, write to the
#   Free Software Foundation, Inc.,
#   51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

import argparse
from collections import OrderedDict
import logging

from phabricator import Phabricator


class TransactionData(OrderedDict):
    def __repr__(self):
        return str(self.transaction())

    def transaction(self):
        """ Return the format expected by Phabricator for its transaction
            parameters.
        """
        output = []
        for key, value in self.iteritems():
            output.append({'type': key, 'value': value})
        return output


def disable_repo_uris(phab, repo_ids):
    # disable all the URIs (if any, from automagic settings)
    if repo_ids is None:
        # all repositories
        found_data = phab.diffusion.repository.search(
                attachments={'uris': True})
        logging.debug('Analyzing all repositories')
    else:
        found_data = phab.diffusion.repository.search(
                constraints={'ids': repo_ids}, attachments={'uris': True})
        logging.debug('Found repository: %s' % (found_data))
    if not found_data.get('data'):
        logging.debug('No repository found or invalid data returned')
        return

    for repo_data in found_data['data']:
        logging.debug('Found data: %s' % (repo_data['attachments']))
        uris = repo_data['attachments']['uris']['uris']
        for uri in uris:
            uri_name = uri['fields']['uri']['display']
            uri_expected_visibility = None
            current_uri_visibility = uri['fields']['display']['raw']
            if uri_name.startswith('git://anongit.kde.org/'):
                # the real URI, set it to be visible
                if current_uri_visibility != 'always':
                    uri_expected_visibility = 'always'
            else:
                # other URIs, set them to be hidden
                if current_uri_visibility != 'never':
                    uri_expected_visibility = 'never'
            if uri_expected_visibility is not None:
                # only change the status if required
                logging.info('Visibility changed to "%s" for URI "%s" '
                             '(repository "%s")' % (uri_expected_visibility,
                                                    uri_name,
                                                    repo_data['fields']
                                                             ['name']))
                uri_t = TransactionData()
                uri_t['display'] = uri_expected_visibility
                phab.diffusion.uri.edit(objectIdentifier=uri['phid'],
                                        transactions=uri_t.transaction())
            else:
                logging.debug('Visibility "%s" unchanged for URI "%s"'
                              '(repository "%s")' % (current_uri_visibility,
                                                     uri_name,
                                                     repo_data['fields']
                                                              ['name']))


def main():
    parser = argparse.ArgumentParser(description='Normalize the visibility '
                                     'of URIs associated to KDE repositories')
    parser.add_argument('-r', '--repository-id', action='append',
                        dest='repo_ids', type=int)
    parser.add_argument('-a', '--all', action='store_true', dest='all')
    parser.add_argument('-v', action='store_true', dest='verbose')
    args = parser.parse_args()

    log_level = logging.INFO
    if args.verbose:
        log_level = logging.DEBUG
    logging.basicConfig(level=log_level)

    repo_ids = None
    if not args.all:
        if not args.repo_ids:
            parser.error('Missing parameter (repository IDs)')
        else:
            repo_ids = args.repo_ids

    phab = Phabricator()

    disable_repo_uris(phab, repo_ids)


if __name__ == '__main__':
    main()
