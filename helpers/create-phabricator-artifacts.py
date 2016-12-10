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
from future.utils import iteritems

from phabricator import APIError as phab_APIError
from phabricator import Phabricator


class TransactionData(OrderedDict):
    def __repr__(self):
        return str(self.transaction())

    def transaction(self):
        """ Return the format expected by Phabricator for its transaction
            parameters.
        """
        output = []
        for key, value in iteritems(self):
            output.append({'type': key, 'value': value})
        return output


def create_repo_mirror(phab, repo_description, repo_name, projects):
    """ Creates a repository which observes an existing repository.
        repo_name is also the repository name.
    """
    # set the required parameters and create the repository
    repo_t = TransactionData()
    repo_t['vcs'] = 'git'
    repo_t['name'] = repo_description
    # handle repositories with namespace
    repo_t['shortName'] = repo_name.replace('/', '-')
    repo_t['projects.add'] = projects
    logging.debug('New repo request: %s' % (repo_t))
    new_repo = phab.diffusion.repository.edit(
            transactions=repo_t.transaction())
    logging.debug('New repo result: %s' % (new_repo))
    new_repo_phid = new_repo['object']['phid']

    # disable all the URIs (if any, from automagic settings)
    found_data = phab.diffusion.repository.search(
            constraints={'phids': [new_repo_phid]}, attachments={'uris': True})
    # 'data' should always exists, but guard against it
    if found_data.get('data'):
        # this is the way to recover the list with all the URIs that have
        # been found
        uris = found_data['data'][0]['attachments']['uris']['uris']
        for uri in uris:
            logging.debug('Disabling URI %s (%s) for repository %s (%s)' %
                          (uri['id'], uri['phid'], repo_name, new_repo_phid))
            disable_uri_t = TransactionData()
            disable_uri_t['display'] = 'never'
            phab.diffusion.uri.edit(objectIdentifier=uri['phid'],
                                    transactions=disable_uri_t.transaction())

    # add the URI which observe the real repository
    uri_t = TransactionData()
    uri_t['repository'] = new_repo_phid
    uri_t['uri'] = 'git://anongit.kde.org/%s' % (repo_name)
    uri_t['io'] = 'observe'
    uri_t['display'] = 'always'
    uri_t['disable'] = False
    logging.debug('New URI request for %s: %s' % (new_repo_phid, uri_t))
    phab.diffusion.uri.edit(transactions=uri_t.transaction())

    # finally, enable the repository
    repo_t = TransactionData()
    repo_t['status'] = 'active'
    logging.debug('Enabling repo %s' % (repo_name))
    new_repo = phab.diffusion.repository.edit(objectIdentifier=new_repo_phid,
                                              transactions=repo_t.transaction()
                                              )

    logging.info('Created repository %s (%s)' % (repo_name, new_repo_phid))
    return new_repo_phid


def create_or_get_project(phab, name):
    found_prj_phid = None
    try:
        logging.debug('Trying to create project %s' % (name))
        new_prj = phab.project.create(name=name, members=[], tags=[])
        found_prj_phid = new_prj['phid']
    except phab_APIError:
        # maybe it already exists, look for it
        logging.debug('Error while creating project %s, checking for it' %
                      (name))
        found_prj = phab.project.search(constraints={'name': '%s' % (name)})
        if found_prj.get('data'):
            # 'name' looks for substrings, so search for the exact match
            for prj_data in found_prj['data']:
                if prj_data['fields']['name'] == name:
                    found_prj_phid = prj_data['phid']
    logging.info('Created or found project %s (%s)' % (name, found_prj_phid))
    return found_prj_phid


def main():
    parser = argparse.ArgumentParser(
            description='Create artifacts on phabricator.kde.org')
    parser.add_argument('-r', '--repository', dest='repo_name')
    parser.add_argument('-d', '--repo-description', dest='repo_description')
    parser.add_argument('-p', '--project', action='append',
                        dest='project_names')
    parser.add_argument('-v', action='store_true', dest='verbose')
    args = parser.parse_args()

    log_level = logging.INFO
    if args.verbose:
        log_level = logging.DEBUG
    logging.basicConfig(level=log_level)

    if not args.repo_name and not args.repo_description:
        parser.error('Missing parameter (repository name or description)')

    phab = Phabricator()  # This will use your ~/.arcrc file
    logging.debug("whoami: %s" % (phab.user.whoami()))

    projects = []
    if args.project_names:
        for project_name in args.project_names:
            prj_phid = create_or_get_project(phab, project_name)
            if prj_phid:
                projects.append(prj_phid)
            else:
                # the else case should not happen (an exception should have
                # occurred before
                logging.warning('Project %s neither created nor found' %
                                (project_name))

    create_repo_mirror(phab, args.repo_description, args.repo_name,
                       projects)


if __name__ == '__main__':
    main()
