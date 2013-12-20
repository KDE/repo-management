$LOAD_PATH << '.'
require 'rubygems'
require 'sinatra'
require 'redirect-http-tarball-sha1'
 
run Sinatra::Application
