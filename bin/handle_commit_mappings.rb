#!/usr/bin/env ruby
=begin
/****************************************************************************************
 * Copyright (c) 2010 Jeff Mitchell <mitchell@kde.org>                                  *
 *                                                                                      *
 * This program is free software; you can redistribute it and/or modify it under        *
 * the terms of the GNU General Public License as published by the Free Software        *
 * Foundation; either version 2 of the License, or (at your option) any later           *
 * version.                                                                             *
 *                                                                                      *
 * This program is distributed in the hope that it will be useful, but WITHOUT ANY      *
 * WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A      *
 * PARTICULAR PURPOSE. See the GNU General Public License for more details.             *
 *                                                                                      *
 * You should have received a copy of the GNU General Public License along with         *
 * this program.  If not, see <http://www.gnu.org/licenses/>.                           *
 ****************************************************************************************/

 This script translates generated commit URLs to end URLs. It attempts to resolve in Redmine
 first; if the commit is not found there, it will return a Gitweb URL. Note that since Gitweb
 URLs are always valid (projects are always in there even if they're not in Redmine) it may
 resolve to a Gitweb URL even before the box syncs a new commit from upstream, because it won't
 yet be found in Redmine.
=end
require 'sinatra'
require 'grit'

$pg = nil
$postgresuser = "commitsscript"
$postgrespass = File.read("/home/git/commit_script_pgpass").chomp

enable :logging

helpers do

  def findGitwebOrRedmineUrl(repoid, changeset)
    # Set up Postgres connection for Redmine. Read in password from a non-public file.
    if not $pg
      require 'pg'
      $pg = PGconn.connect("projects.kde.org", 5432, '', '', "redmine", $postgresuser, $postgrespass)
    end
    # Every git repository should have a kde-repo-uid file that has a value computed from a hash
    # of its path. In addition, there may be a kde-repo-nick file containing a more friendly name.
    # This more friendly name is used when the URL is generated, if it exists. These are used to
    # populate the files in /home/git/repo-uid-mappings, which map an identifier to the actual 
    # directory, offset from /repositories, that contains the git directory. This path can then
    # be used in the query in the Redmine DB or directly in the Gitweb URL.
    if not File.exists?("/home/git/repo-uid-mappings/#{repoid}")
      logger.info( "Cannot find repoid, was looking for /home/git/repo-uid-mappings/#{repoid}" )
      return nil
    end
    path = File.read("/home/git/repo-uid-mappings/#{repoid}").chomp
    if not File.exists?("/repositories/#{path}")
      logger.info( "Cannot find the repository specified by the UID" )
      return nil
    end

    # Grit doesn't properly check that SHA1s aren't actually too big
    if changeset.length > 40
      logger.info( "SHA size is too big" )
      return nil
    end

    # Get the full SHA1
    sha1 = changeset
    begin
      repo = Grit::Repo.new("/repositories/#{path}")
      commit = repo.commit("#{sha1}")
      if commit.nil?
        logger.info( "Could not find commit" )
        return nil
      else
        sha1 = commit.sha
      end
    rescue Exception
      logger.info( "Encountered error creating grit object" )
      return nil
    end

    # See if the commit exists in Redmine
    execstring = "select projects.id AS projectsid, identifier AS id, parent_id AS parentid, url AS url from projects LEFT JOIN repositories on projects.id = repositories.project_id LEFT JOIN changesets on changesets.repository_id = repositories.id where changesets.revision = '#{sha1}';"
    begin
        res = $pg.exec(execstring)
    rescue PGError
        $pg = PGconn.connect("projects.kde.org", 5432, '', '', "redmine", $postgresuser, $postgrespass)
        res = $pg.exec(execstring)
    end
    # TODO: Not sure that this will properly handle finding the *right* repository with a clone...
    # it only checks one DB path, because it assumes one result. Might have to check each DB path in
    # turn until we find the one matching the repository path.
    if res.nil? or res.ntuples < 1 or res[0].nil? or res[0]["projectsid"].nil? or res[0]["id"].nil? or res[0]["parentid"].nil? or res[0]["url"].nil?
      return "http://quickgit.kde.org/?p=#{path}&a=commit&h=#{sha1}"
    end

    # Create the path that we can use to walk the Redmine DB
    reppath = "/repositories/" + path
    # Check the ASCII value too because for some reason it doesn't always work checking the char
    reppath.chop! if reppath[reppath.length-1] == 47 or reppath[reppath.length-1] == '/'
    dbpath = res[0]["url"]
    dbpath.chop! if dbpath[dbpath.length-1] == 47 or dbpath[dbpath.length-1] == '/'
    # Create our initial final path based on the found identifier
    finpath = res[0]["id"]
    if reppath == dbpath
      # Is there a parent?
      if not res[0]["parentid"].nil?
        # Right repo; do recursive walk, adding on parent identifiers to the front of the final path
        execstring = "select id AS projectsid, identifier AS id, parent_id AS parentid from projects where id = #{res[0]["parentid"]}"
        res = $pg.exec(execstring)
        until res[0]["parentid"].nil?
          finpath = res[0]["id"] + '/' + finpath
          execstring = "select id AS projectsid, identifier AS id, parent_id AS parentid from projects where id = #{res[0]["parentid"]}"
          res = $pg.exec(execstring)
        end
        finpath = res[0]["id"] + "/" + finpath
      end
      return "http://projects.kde.org/projects/#{finpath}/repository/revisions/#{sha1}"
    else
      # At this point we know the commit exists in the repo but if not found above then it's not in Redmine so return quickgit
      return "http://quickgit.kde.org/?p=#{path}&a=commit&h=#{sha1}"
    end
  end

end

get '/robots.txt' do
  content_type 'text/plain'
  return "User-agent: *\nDisallow: /"
end

# Proper URL format? Find a URL, or redirect to Projects.
get /^\/(([a-zA-Z0-9][a-zA-Z0-9_\.\-]+[a-zA-Z0-9]\/)+)([a-fA-F0-9]+)/ do |repoid, lastval, changeset|
  # repoid will match with a / at the end, so chop it
  # substitute the magic value used in place of / in the path since the repo-uid mapping directory is flat
  repoid.downcase!
  url = findGitwebOrRedmineUrl(repoid.chop.gsub(/\//, "__NICK-MAGIC__"), changeset)
  if url.nil?
    return '<HTML><HEAD><META HTTP-EQUIV="refresh" CONTENT="3;URL=http://projects.kde.org"></HEAD><BODY>The repo/commit cannot be found or the commit is non-unique. Redirecting to <a href="http://projects.kde.org">KDE Projects</a>...</BODY></HTML>' 
  else
    redirect url
  end
end

# Anything else, redirect to Projects.
get '*' do
  return '<HTML><HEAD><META HTTP-EQUIV="refresh" CONTENT="3;URL=http://projects.kde.org"></HEAD><BODY>Invalid URL. Redirecting to <a href="http://projects.kde.org">KDE Projects</a>...</BODY></HTML>' 
end
