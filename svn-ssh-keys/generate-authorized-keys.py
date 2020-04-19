#!/usr/bin/python3
import os
import sys
import time
import yaml
import gitlab
import argparse

# Gather the command line arguments we need
parser = argparse.ArgumentParser(description='Utility to generate SSH authorized_keys file based on a Gitlab group and the keys on that Gitlab instance')
parser.add_argument('--config', help='Path to the configuration file to work with', required=True)
args = parser.parse_args()

# Make sure our configuration file exists
if not os.path.exists( args.config ):
	print("Unable to locate specified configuration file: %s".format(args.config))
	sys.exit(1)

# Read in our configuration
configFile = open( args.config, 'r' )
configuration = yaml.load( configFile, Loader=yaml.FullLoader )

# Connect to the upstream Gitlab server we will be working with
# To do this, we need to get our credentials and hostname first
gitlabHost  = configuration['Gitlab']['instance']
gitlabToken = configuration['Gitlab']['token']
# Now we can actually connect
gitlabServer = gitlab.Gitlab( gitlabHost, private_token=gitlabToken )

# Step 1 is to retrieve the group whose membership listing we will be working off...
# Along with the membership list of that group (we have to specify all=True, otherwise we will only get the first 20 members)
gitlabGroup   = gitlabServer.groups.get( configuration['Gitlab']['group-path'] )
gitlabMembers = gitlabGroup.members.list( all=True )

# Step 2 is to check whether we need to limit the list of people we consider for inclusion in the authorized_keys file we produce to a given whitelist
# This can be done using a text file with one line for each username that should be included (subject to them also being a member of the above group)
if configuration['SSH']['member-whitelist'] is not None:
	# Load the whitelist
	whitelistFile    = open( configuration['SSH']['member-whitelist'], 'r', encoding='utf-8' )
	whitelistedUsers = whitelistFile.read().splitlines()
	whitelistFile.close()

	# Now filter out the list of Gitlab group members we retrieved earlier to ensure they are all on the whitelist
	gitlabMembers = [ member for member in gitlabMembers if member.username in whitelistedUsers ]

# Step 3 is to retrieve all the SSH keys from Gitlab
# Unfortunately there is no nice API to do this, we have to make one HTTP request per member
# To avoid creating unnecessary load on the Gitlab server, we sleep for 1 second between each request
knownKeys = []

for member in gitlabMembers:
	# Unfortunately the construct returned by gitlabGroup.members.list() does not provide access to SSH Keys
	# As we don't need any additional information about the user though, we can just lazily retrieve them
	# This has the benefit of not hitting Gitlab for user information we are not going to be using
	gitlabUser = gitlabServer.users.get( member.id, lazy=True )

	# Retrieve the keys...
	sshKeys = gitlabUser.keys.list()

	# Save them for later
	for key in sshKeys:
		entry = ( member.username, key )
		knownKeys.append( entry )

	# Now we wait for 1 second to keep the load on Gitlab low
	time.sleep(1)

# Step 4 is to finally write out our authorized_keys file
# This is printed to stdout for ease of diagnostic and storage (in the event of needing to use it via something like sudo)
# We start with a line to indicate we generated this...
print("## AUTOMATICALLY GENERATED BY generate-authorized-keys.py")

# Now we start printing out keys...
for username, key in knownKeys:
	# Determine the restriction to be applied to this key
	restriction = configuration['SSH']['key-restrictions'].format( username=username )

	# Now generate the line...
	keyline = "{restriction} {key}".format( restriction=restriction, key=key.key )
	
	# And output it for use
	print( keyline )

# All done!
sys.exit(0)
