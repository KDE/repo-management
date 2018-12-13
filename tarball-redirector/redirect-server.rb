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
require 'sinatra'

get %r{/updateRepo/(.*)} do |url|
  path = ENV['HOME'] + '/repositories/' + url
  if not File.exists?(path) or not File.directory?(path)
    return 'FAIL'
  end
  require 'git'
  begin
    repo = Git.bare(path)
    repo.remote('origin').fetch
    return 'OK'
  rescue Exception
    return 'FAIL'
  end
end

get '*' do
  status 404
  "Not found"
end
