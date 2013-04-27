$:.unshift(File.dirname(__FILE__))
require 'rubygems'
require 'sinatra'
require 'handle_commit_mappings'

run Sinatra::Application
