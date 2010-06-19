#!/usr/bin/ruby

require 'fileutils'
puts File.dirname(__FILE__)
REPO = ARGV[0]
NAME = ARGV[1]
BASE = Dir.pwd

if ARGV.count != 2 then
   puts "addrepo.rb [git repo url] [name of project]"
   exit
end

Dir.mkdir('stage') unless File.exists?('stage')
Dir.mkdir('target') unless File.exists?('target')

Dir.chdir('stage')
puts "git clone #{REPO} #{NAME}"
`git clone #{REPO} #{NAME}`
Dir.chdir(NAME)
`git remote add target #{BASE}/target/#{NAME}.git`
Dir.chdir("#{BASE}/target")
`git clone --bare #{BASE}/stage/#{NAME} #{NAME}.git`
Dir.chdir(BASE)
FileUtils.cp("#{File.dirname(__FILE__)}/update.sample", "#{BASE}/target/#{NAME}.git/hooks/update")

puts "Edit #{BASE}/target/#{NAME}.git/hooks/update"
