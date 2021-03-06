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


try:
    sqlite_ok = True
    import cyclone.sqlite
except ImportError, sqlite_err:
    sqlite_ok = False

import MySQLdb
import cyclone.redis
import functools

from twisted.internet import defer
from twisted.internet import reactor
from twisted.python import log

from twisted.internet.protocol import ReconnectingClientFactory
from twisted.protocols.memcache import MemCacheProtocol

from images import txdbapi


class users(txdbapi.DatabaseModel):
    pass


def DatabaseSafe(method):
    """This decorator function makes all database calls safe from connection
     errors. It returns an HTTP 503 when either redis or mysql are temporarily
     disconnected.

     @DatabaseSafe
     def get(self):
        now = yield self.mysql.runQuery("select now()")
        print now
    """
    @defer.inlineCallbacks
    @functools.wraps(method)
    def run(self, *args, **kwargs):
        try:
            r = yield defer.maybeDeferred(method, self, *args, **kwargs)
        except cyclone.redis.ConnectionError, e:
            m = "redis.ConnectionError: %s" % e
            log.msg(m)
            raise cyclone.web.HTTPError(503, m)  # Service Unavailable
        except (MySQLdb.InterfaceError, MySQLdb.OperationalError), e:
            m = "mysql.Error: %s" % e
            log.msg(m)
            raise cyclone.web.HTTPError(503, m)  # Service Unavailable
        else:
            defer.returnValue(r)

    return run


class DatabaseMixin(object):
    mysql = None
    redis = None
    tokyotyrant = None
    sqlite = None

    @classmethod
    def setup(cls, conf):
        if "sqlite_settings" in conf:
            if sqlite_ok:
                DatabaseMixin.sqlite = \
                cyclone.sqlite.InlineSQLite(conf["sqlite_settings"].database)
            else:
                log.err("SQLite is currently disabled: %s" % sqlite_err)

        if "tokyotyrant_settings" in conf:
            ttfactory = MemcacheClientFactory()
            reactor.connectTCP(conf["tokyotyrant_settings"].host, 
                               conf["tokyotyrant_settings"].port, 
                               ttfactory)


        if "redis_settings" in conf:
            if conf["redis_settings"].get("unixsocket"):
                DatabaseMixin.redis = \
                cyclone.redis.lazyUnixConnectionPool(
                              conf["redis_settings"].unixsocket,
                              conf["redis_settings"].dbid,
                              conf["redis_settings"].poolsize)
            else:
                DatabaseMixin.redis = \
                cyclone.redis.lazyConnectionPool(
                              conf["redis_settings"].host,
                              conf["redis_settings"].port,
                              conf["redis_settings"].dbid,
                              conf["redis_settings"].poolsize)

        if "mysql_settings" in conf:
            txdbapi.DatabaseModel.db = DatabaseMixin.mysql = \
            txdbapi.ConnectionPool("MySQLdb",
                                  host=conf["mysql_settings"].host,
                                  port=conf["mysql_settings"].port,
                                  db=conf["mysql_settings"].database,
                                  user=conf["mysql_settings"].username,
                                  passwd=conf["mysql_settings"].password,
                                  cp_min=1,
                                  cp_max=conf["mysql_settings"].poolsize,
                                  cp_reconnect=True,
                                  cp_noisy=conf["mysql_settings"].debug)

            # Ping MySQL to avoid timeouts. On timeouts, the first query
            # responds with the following error, before it reconnects:
            #   mysql.Error: (2006, 'MySQL server has gone away')
            #
            # There's no way differentiate this from the server shutting down
            # and write() failing. To avoid the timeout, we ping.
            @defer.inlineCallbacks
            def _ping_mysql():
                try:
                    yield cls.mysql.runQuery("select 1")
                except Exception, e:
                    log.msg("MySQL ping error:", e)
                else:
                    if conf["mysql_settings"].debug:
                        log.msg("MySQL ping: OK")

                reactor.callLater(conf["mysql_settings"].ping, _ping_mysql)

            if conf["mysql_settings"].ping > 1:
                _ping_mysql()


class MemcacheClientFactory(ReconnectingClientFactory, DatabaseMixin):
    connected = False

    def startedConnecting(self, connector):
        pass

    def buildProtocol(self, addr):
        self.resetDelay()
        self.connected = True
        self.protocol = MemCacheProtocol()
        DatabaseMixin.tokyotyrant = self.protocol
        return self.protocol

    def clientConnectionLost(self, connector, reason):
        self.connected = False
        DatabaseMixin.tokyotyrant = None
        ReconnectingClientFactory.clientConnectionLost(self, connector, reason)
        self.retry(connector)

    def clientConnectionFailed(self, connector, reason):
        ReconnectingClientFactory.clientConnectionFailed(self, connector,
                                                         reason)
        self.retry(connector)
