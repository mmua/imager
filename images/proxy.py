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
import traceback
import sys

from tempfile import NamedTemporaryFile
import os.path
from os import rename,link,makedirs,chmod
from hashlib import sha1

from datetime import datetime

from twisted.internet import defer
from twisted.python import log

import json

from images.utils import BaseHandler
from images.utils import SessionMixin
from images.utils import TemplateFields

from images.storage import DatabaseMixin, MemcacheClientFactory
from images.imager  import ImagerMixin

def _makedirs(dstdir):
    try:
        makedirs(dstdir)
    except OSError, e:
       if e.errno == 17: # dir exists already
           pass
       else:
           raise e

class DownloadHandler(BaseHandler, DatabaseMixin, ImagerMixin):
    @defer.inlineCallbacks
    def get(self, uri):
        host = 'www.f1news.ru'
        url = 'http://%s/%s' % (host, uri)
        try:
            response = yield cyclone.httpclient.fetch(url, followRedirect=1, maxRedirects=2)
	    if response.code == 200:
                h = sha1()
                h.update(response.body)
                sha1sum = h.hexdigest()

                # save file to storage
                dstdir = os.path.join(ImagerMixin.base, host, sha1sum[0:2], sha1sum[2:4], sha1sum)
                _makedirs(dstdir)
               
                dst = os.path.join(dstdir, os.path.basename(uri))
	        with NamedTemporaryFile(dir=os.path.join(ImagerMixin.base, "tmp"), delete=False) as f:
		    f.write(response.body)
                    try:
		        rename(f.name, dst)
                        chmod(dst, 0644)
		    except OSError, e:
                        print "can't move file: %s" % str(e)

                # make link for nginx
                filedst = os.path.join(ImagerMixin.base, host, uri)
                dstdir = os.path.dirname(filedst)
                _makedirs(dstdir)

                try:
                    link(dst, filedst)
                except OSError, e:
                   if e.errno == 17: # dir exists already
                       pass
                   else:
                       raise e

                # save file info to database
                h = sha1() 
                h.update(uri)
                urisha1 = h.hexdigest()
                data = {'path': dst, 'sha1': sha1sum, 'uri': uri, 'urisha1': urisha1, 'resizes': [] }
                try:
                    yield DatabaseMixin.tokyotyrant.set(urisha1, json.dumps(data))
                except Exception, e:
	            res = {'status': 'error', 'message': 'database exception', 'exception': str(e)}
                else:
                    res = {'status': 'ok', 'path': dst, 'sha1': sha1sum, 'uri': uri, 'urisha1': urisha1, 'resizes': []}
	    else:
                self.set_status(response.code)
	        res = {'status': 'error', 'code': response.code, 'message': response.body}

        except Exception, e:
	    print "proxy exception: %s" % str(e)
            print "Exception in user code:"
            print '-'*60
            traceback.print_exc(file=sys.stdout)
            print '-'*60
            self.set_status(500)
	    res = {'status': 'error', 'code': 500, 'message': 'proxy error'}

        self.write(json.dumps(res))
