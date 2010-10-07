#!/usr/bin/env ruby
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

  def findGitwebUrl(repoid, changeset)
    if not File.exists?("/home/git/repo-uid-mappings/#{repoid}")
      return nil
    end
    path = File.read("/home/git/repo-uid-mappings/#{repoid}").chomp
    if not File.exists?("/repositories/#{path}")
      return nil
    end
    return "http://gitweb.kde.org/#{path}/commit/#{changeset}"
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

get %r{/g/([a-zA-Z0-9]+)/([a-zA-Z0-9]+)} do |repoid, changeset|
  url = findGitwebUrl(repoid, changeset)
  if url.nil?
    redirect "http://projects.kde.org/"
  else
    redirect url
  end
end

get '*' do
  redirect "http://projects.kde.org/"
end
