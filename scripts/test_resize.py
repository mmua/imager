from twisted.internet import protocol, utils, reactor, defer
from twisted.python import failure
from cStringIO import StringIO

class ImagerProtocol(protocol.ProcessProtocol):

    def connectionMade(self):
        self.df = None
        self.pid = self.transport.pid
        print "started %s" % self.pid
        print self.transport

    def write(self, data):
        assert self.df is None
        self.df = defer.Deferred()
        self.transport.write(data)
        print "data written %s" % data
        return self.df

    def errReceived(self, data):
        try:
            print "process %s got response" % self.pid
            self.df.callback(data)
            self.df = None
        except Exception, e:
            print str(e)
            self.df.errback(e)

    def outReceived(self, data):
        try:
            print "process %s got response" % self.pid
            self.df.callback(data)
            self.df = None
        except Exception, e:
            print str(e)
            self.df.errback(e)

    def noResponse(self, err):
        print "no response %s" % self.pid
        self.transport.loseConnection()

    def processExited(self, reason):
        print "processExited %s, status %s" % (self.pid, reason.value.exitCode,)

@defer.inlineCallbacks
def resize(pp):
    print "write data"
    res = yield pp.write('{"src": "test.jpg", "dst": "100x50.png", "cmd": "resize", "resize": "100x50"}' + "\n")
    print res

if __name__ == '__main__':
    pp = ImagerProtocol()
    subprocesses = {}
    command = ['/var/www/images.f1news.ru/scripts/resize_image.py']
    subprocess = reactor.spawnProcess(pp, command[0], command, {})
    print subprocess
    subprocesses[subprocess.pid] = subprocess
    reactor.callLater(3, resize, pp)
    reactor.run()

