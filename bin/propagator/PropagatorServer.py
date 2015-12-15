#!/usr/bin/python3
#
# Copyright 2015 Boudhayan Gupta <bgupta@kde.org>
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
# 3. Neither the name of KDE e.V. (or its successor approved by the
#    membership of KDE e.V.) nor the names of its contributors may be used
#    to endorse or promote products derived from this software without
#    specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE AUTHOR "AS IS" AND ANY EXPRESS OR
# IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES
# OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
# IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT
# NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF
# THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import sys
import os
import asyncio
import signal

from PropagatorProtocol import CommandProtocol

def main():

    # check that our unix socket path does not exist yet
    socketPath = os.path.expanduser("~/.propagator.sock")
    if (os.path.exists(socketPath)):
        print("ERROR: PropagatorServer is either already running, or exited uncleanly the last time.")
        print("If you are sure the server is not running, delete %s and try again." % socketPath)
        sys.exit(1)

    # init the event loop and inject the server coroutine
    loop = asyncio.get_event_loop()
    serverCoro = loop.create_unix_server(CommandProtocol, socketPath)
    serverJob = loop.run_until_complete(serverCoro)
    print("PropagatorServer has PID {} and is listening at {}".format(os.getpid(), serverJob.sockets[0].getsockname()))

    # define the cleanup handler here
    def cleanup():
        print("PropagatorServer is shutting down...")

        serverJob.close()
        loop.run_until_complete(serverJob.wait_closed())
        loop.close()
        os.unlink(socketPath)

        print("PropagatorServer has shut down successfully")
        sys.exit(0)

    # hook up the signal handler. note that we can't listen for SIGKILL, so if
    # we're killed with kill -9 the server won't start again until we remove
    # the socket file
    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)

    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        cleanup()

if __name__ == "__main__":
    main()
