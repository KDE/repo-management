#!/usr/bin/env python
# -*- coding: utf-8 -*-

#   Copyright 2011 Luca Beltrame <einar@heavensinferno.net>
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

import json
import logging
import sys
import urllib
import urlparse

from rest_client import Connection

# Basic constants

REVIEWBOARD_URL = "http://testrb.vidsolbach.de"


def setup_logger():

    """Setup a logging instance to be used for error reporting."""

    logger = logging.getLogger("reviewboard")
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter("%(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)

def read_credentials():

    """Read username and password from a file.

    The file should contain a single line in the form "username:password".

    Return:
        A (username, password) tuple.

    """

    credential_file = os.getenv('HOME') + "/reviewboard-credentials"
    with open(credential_file) as handle:
        credentials = handle.readline().strip()
        username, password = credentials.split(":")

    return username, password

def close_review(review_id, commit, committer):

    """Close a review request on Reviewboard.

    Append a message stating that the review request has been closed
    by a commit, and then mark the actual review as submitted.

    Username and passwords are read from a local file, to prevent hardcoding in
    the code. Errors are handled with a logger, ranging from critical (JSON
    decoding errors) to error (when Reviewboard answers with an error)

    Parameters:
        - review_id - the ID to close
        - commit - the commit SHA1
        - committer - the committer's username
    """

    reviewboard_url = urlparse.urljoin(REVIEWBOARD_URL, "api")

    username, password = read_credentials()

    # Logger is a singleton
    logger = logging.getLogger("reviewboard")
    logger.setLevel(logging.INFO)

    connection = Connection(reviewboard_url, username=username,
                            password=password)
    # HTML-encode the message to avoid unpleasant side effects
    message = urllib.quote("This review has been submitted with commit "
                           "%s by %s." % (commit, committer))

    # Resources for replying and for submitting
    submit_resource = "review-requests/%s" % review_id
    reply_resource = "review-requests/%s/reviews/" % review_id

    # Post a message announcing the submission
    response = connection.request_post(reply_resource,
                                       body="public=True&body_top=%s" %
                                       message)
    try:
        response = json.loads(response["body"])
    except ValueError:
        logging.critical("Malformed response received from Reviewboard."
                         " Contact the KDE sysadmins.")
        return

    if response["stat"] != "ok":
        logger.error("An error occurred while accessing Reviewboard.")
        logger.error(response["err"]["msg"])
        return

    # Change the actual status
    response = connection.request_put(submit_resource,
                                      body="status=submitted")

    try:
        response = json.loads(response["body"])
    except ValueError:
        logging.critical("Malformed response received from Reviewboard."
                         " Contact the KDE sysadmins.")
        return

    if response["stat"] != "ok":
        logger.error("An error occurred while accessing Reviewboard.")
        logger.error(response["err"]["msg"])
        return

    logger.info("Review request %s successfully closed." % review_id)

def usage():

    print "Usage: update_review <review-id> <commit sha1> <committer>"
    sys.exit(0)

def main():

    setup_logger()

    if len(sys.argv) != 4:
        usage()

    review_id = sys.argv[1]
    commit_id = sys.argv[2]
    committer = sys.argv[3]

    close_review(review_id, commit_id, committer)
    sys.exit(0)

if __name__ == '__main__':
    main()