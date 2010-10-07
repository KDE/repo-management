#!/usr/bin/env ruby
require 'postgres'
require 'sinatra'
require 'pp'

postgresuser = "commitsscript"
postgrespass = File.read("/home/git/commit_script_pgpass").chomp
$pg = PGconn.connect("127.0.0.1", 5432, '', '', "redmine", postgresuser, postgrespass)

helpers do
  def findRedmineUrl(changeset)
    execstring = "select identifier from projects LEFT JOIN repositories on projects.id = repositories.project_id LEFT JOIN changesets on changesets.repository_id = repositories.id where changesets.revision = '#{changeset}';"
    pp execstring
    res = $pg.exec(execstring)
    pp res
    pp res[0].nil?
    if not res[0].nil?
      return "http://projects.kde.org/projects/#{res[0][0]}/repository/revisions/#{changeset}"
    end
    return nil
  end
end

get %r{/r/([a-zA-Z0-9]+)} do |changeset|
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
