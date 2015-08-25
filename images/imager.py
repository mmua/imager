# coding: utf-8
#
# Copyright 2013 Maxim Moroz
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


from twisted.internet import defer
from twisted.internet import reactor, protocol, defer
from twisted.python import log
from collections import deque

import json

class ImagerProtocol(protocol.ProcessProtocol):

    def connectionMade(self):
        self.df = None
        self.pid = self.transport.pid
        print "started %s" % self.pid

    def write(self, data):
        assert self.df is None
        self.df = defer.Deferred()
        self.transport.write(data)
        print "data written %s" % data
        return self.df

    def errReceived(self, data):
        try:
            print "process %s got err response" % self.pid
            if self.df:
                self.df.callback(data)
                self.df = None
        except Exception, e:
            print "Exception goes here:", str(e)
            if self.df:
                self.df.errback(e)

    def outReceived(self, data):
        try:
            print "process %s got response" % self.pid
            self.df.callback(data)
            self.df = None
        except Exception, e:
            print "Got exception", str(e)
            self.df.errback(e)

    def noResponse(self, err):
        print "no response %s" % self.pid
        self.transport.loseConnection()

    def processExited(self, reason):
        print "processExited %s, status %s" % (self.pid, reason.value.exitCode,)
        del ImagerMixin.subprocesses[self.pid]
        ImagerMixin.respawnImager()

    def idle(self):
        return self.df is None

class ImagerMixin(object):
    subprocesses = {}
    running = {}
    waiting = deque()
    base = "/var/www/images.f1news.ru/frontend/static/i"
    resize_base = "/var/www/images.f1news.ru/frontend/static/r"
    
    @classmethod
    def setup(cls, conf):
        for i in xrange(16):
            cls.respawnImager()

    @classmethod
    def respawnImager(cls):
        pp = ImagerProtocol()
        subprocesses = {}
        command = ['/var/www/images.f1news.ru/scripts/resize_image.py']
        subprocess = reactor.spawnProcess(pp, command[0], command, {})
        cls.subprocesses[subprocess.pid] = pp

    @classmethod
    def resize(cls, src, dst, resize):
        df = defer.Deferred()
        cmd = {'cmd': 'resize', 'src': src, 'dst': dst, 'resize': resize, 'df': df}
        cls.waiting.appendleft(cmd)
        if len(cls.running) < len(cls.subprocesses):
            cls.schedule()
        return df

    @classmethod
    def crop(cls, src, dst, resize):
        df = defer.Deferred()
        cmd = {'cmd': 'crop', 'src': src, 'dst': dst, 'resize': resize, 'df': df}
        cls.waiting.appendleft(cmd)
        if len(cls.running) < len(cls.subprocesses):
            cls.schedule()
        return df

    @classmethod
    def schedule(cls):
        for pid, pp in cls.subprocesses.iteritems():
            if pp.idle() and cls.waiting:
                cmd = cls.waiting.pop()
                res = cmd.pop('df')
                cls.running[pp.pid] = res
                df = pp.write(json.dumps(cmd) + "\n")
                def _gotData(data):
                    del cls.running[pp.pid]
                    if len(cls.running) < len(cls.subprocesses):
                        reactor.callLater(0, cls.schedule)
                    try:
                        data = json.loads(data)
                    except ValueError, e:
                        print data
                        data = {'status': 'error', 'data': data}
                    status = data.pop('status')
                    if status == 'ok':
                        res.callback(data)
                    else:
                        res.errback(data)
                df.addCallback(_gotData)
                break


