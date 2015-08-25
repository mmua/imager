# coding: utf-8
#
# Copyright 2013 Foo Bar
# Powered by cyclone
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.


import OpenSSL
import cyclone.escape
import cyclone.locale
import cyclone.mail
import cyclone.web
import cyclone.httpclient
import hashlib
import random
import string
import json
import mimetypes
import os.path

from datetime import datetime
from hashlib import sha1

from twisted.internet import defer
from twisted.python import log

from images.utils import BaseHandler
from images.utils import SessionMixin
from images.utils import TemplateFields

from images.storage import DatabaseMixin
from images.imager  import ImagerMixin


class ImageHandler(BaseHandler, DatabaseMixin):
   
    @defer.inlineCallbacks
    def get(self, uri):
        url = "http://127.0.0.1:8088/" + uri
        try:
            response = yield cyclone.httpclient.fetch(url, followRedirect=1, maxRedirects=2)
            if response.code == 200:
                self.clear()
                tp, enc = mimetypes.guess_type(uri) 
                self.set_header("Content-Type", tp)
                self.add_header('X-Accel-Redirect', '/a/%s' % uri)
            else:
                print "code %s" % response.code
                self.set_header("Content-Type", "text/plain; charset=utf-8")
                self.set_status(response.code)
                self.write(response.body)
        except Exception, e:
            print "proxy request got exception: %s" % str(e) 
            self.write(uri)

class ImageResizeHandler(ImageHandler, DatabaseMixin, ImagerMixin):
    def initialize(self, cmd = 'resize'):
        self.cmd = cmd

    @defer.inlineCallbacks
    def get(self, uri):
        host = 'www.f1news.ru'
        resize, uri = uri.split('/', 1)
        h = sha1()
        h.update(uri)
        urisha1 = h.hexdigest()

        if DatabaseMixin.tokyotyrant is None:
            print "database gone"  
            self.set_status(502)
            self.write('database error')
            defer.returnValue(None)

        try:
            res, data = yield DatabaseMixin.tokyotyrant.get(urisha1)
        except Exception, e:
            print "Got exception: %s" % str(e)
            self.set_status(502)
            self.write('database error')
            defer.returnValue(None)

        if res != 0:
            self.set_status(503)
            defer.returnValue(None)

        if not data:
            print "no data for %s %s" % (uri, urisha1) 
            url = "http://127.0.0.1:8088/" + uri
            try:
                response = yield cyclone.httpclient.fetch(url, followRedirect=1, maxRedirects=2)
                if response.code == 200:
                    res, data = yield DatabaseMixin.tokyotyrant.get(urisha1)
                else:
                    self.set_header("Content-Type", "text/plain; charset=utf-8")
                    self.set_status(response.code)
                    self.write(response.body)
                    defer.returnValue(None)
            except Exception, e:
                print "proxy request got exception: %s" % str(e) 
                self.set_status(502)
                self.write('proxy error')
                defer.returnValue(None)

        data = json.loads(data)
        # FIXME: we already know image sizes so multiple resizes can map to one - so we need to map requested resize to actual one 
        resize = unicode(resize)
        if True or resize not in data['resizes']: # resize before. Beware of the dog! Check approved resizes!
            resize_dst = os.path.join(ImagerMixin.resize_base, host, self.cmd, resize, uri)
            try:
                if self.cmd == 'crop':
                    res = yield ImagerMixin.crop(data['path'], resize_dst, resize)
                else:
                    res = yield ImagerMixin.resize(data['path'], resize_dst, resize)
                data['resizes'].append(resize)
                seen = set()
                seen_add = seen.add
                data['resizes'] = [ x for x in data['resizes'] if x not in seen and not seen_add(x)]
                yield DatabaseMixin.tokyotyrant.set(urisha1, json.dumps(data))
                self.clear()
                tp, enc = mimetypes.guess_type(uri) 
                self.set_header("Content-Type", tp)
                self.add_header('X-Accel-Redirect', '/b/%s/%s/%s' % (self.cmd, resize, uri))
            except Exception, e: 
                self.set_status(503)
                self.write("can't resize image")
                defer.returnValue(None)
                
        print str(data)
