#!/usr/bin/python -W ignore::DeprecationWarning
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
import os
import urllib
import urlparse

import requests

# Basic constants

REVIEWBOARD_URL = "https://git.reviewboard.kde.org"
DEFAULT_LEVEL = logging.INFO


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

def close_review(review_id, commit, committer, changed_ref):

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
    logger.setLevel(DEFAULT_LEVEL)

    message = urllib.quote("This review has been submitted with commit "
                           "%s by %s to %s." % (commit, committer, changed_ref))

    # Resources for replying and for submitting
    submit_resource = "review-requests/%s" % review_id
    reply_resource = "review-requests/%s/reviews/" % review_id

    submit_url = urlparse.urljoin(reviewboard_url, submit_resource)
    reply_url = urlparse.urljoin(reviewboard_url, reply_resource)

    # Post a message announcing the submission
    logger.debug("Sending comment")

    post_reply = dict(public=True, body_top=message)

    request = requests.post(reply_url, auth=(username, password),
            params=post_reply) 

    try:
        response = json.loads(request.content)
    except ValueError:
        logging.critical("Malformed response received from Reviewboard."
                         " Contact the KDE sysadmins.")
        return

    if response["stat"] != "ok":
        logger.error("An error occurred while accessing Reviewboard.")
        logger.error(response["err"]["msg"])
        return

    # Change the actual status
    logger.debug("Sending status")

    status_request = requests.put(submit_url, auth=(username, password),
            params=dict(body="status=submitted"))

    try:
        response = json.loads(status_request.content)
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

    if len(sys.argv) != 5:
        logger = logging.getLogger("reviewboard")
        logger.setLevel(DEFAULT_LEVEL)
        # Only output information when we're using debug
        logger.debug(sys.argv)
        usage()

    review_id = sys.argv[1]
    commit_id = sys.argv[2]
    committer = sys.argv[3]
    ref_change = sys.argv[4]

    close_review(review_id, commit_id, committer, ref_change)
    sys.exit(0)

if __name__ == '__main__':
    main()
