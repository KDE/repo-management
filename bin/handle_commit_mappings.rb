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
=end
require 'postgres'
require 'sinatra'

postgresuser = "commitsscript"
postgrespass = File.read("/home/git/commit_script_pgpass").chomp
$pg = PGconn.connect("127.0.0.1", 5432, '', '', "redmine", postgresuser, postgrespass)

helpers do
  def findRedmineUrl(changeset)
    execstring = "select identifier from projects LEFT JOIN repositories on projects.id = repositories.project_id LEFT JOIN changesets on changesets.repository_id = repositories.id where changesets.revision = '#{changeset}';"
    res = $pg.exec(execstring)
    if not res[0].nil?
      return "http://projects.kde.org/projects/#{res[0][0]}/repository/revisions/#{changeset}"
    end
    return nil
  end

  def findGitwebOrRedmineUrl(repoid, changeset)
    if not File.exists?("/home/git/repo-uid-mappings/#{repoid}")
      return findRedmineUrl(changeset)
    end
    path = File.read("/home/git/repo-uid-mappings/#{repoid}").chomp
    puts path
    if not File.exists?("/repositories/#{path}")
      return nil
    end
    execstring = "select identifier, url from projects LEFT JOIN repositories on projects.id = repositories.project_id LEFT JOIN changesets on changesets.repository_id = repositories.id where changesets.revision = '#{changeset}';"
    res = $pg.exec(execstring)
    puts res
    if not res[0].nil?
      reppath = "/repositories/" + path
      puts reppath
      puts res[0][1]
      if reppath == res[0][1]
        return "http://projects.kde.org/projects/#{res[0][0]}/repository/revisions/#{changeset}"
      end
    end
    return "http://gitweb.kde.org/#{path}/commit/#{changeset}"
  end

end

get %r{/([a-zA-Z0-9]+)/([a-zA-Z0-9]+)} do |repoid, changeset|
  url = findGitwebOrRedmineUrl(repoid, changeset)
  if url.nil?
    redirect "http://projects.kde.org/"
  else
    redirect url
  end
end

get %r{/([a-zA-Z0-9]+)} do |changeset|
  url = findRedmineUrl(changeset)
  if url.nil?
    redirect "http://projects.kde.org/"
  else
    redirect url
  end
end

get '*' do
  redirect "http://projects.kde.org/"
end
