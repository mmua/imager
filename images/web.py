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


import cyclone.locale
import cyclone.web

from images import views,proxy,image
from images import config
from images.storage import DatabaseMixin
from images.imager  import ImagerMixin


class Application(cyclone.web.Application):
    def __init__(self, config_file):
        conf = config.parse_config(config_file)
        handlers = [
            (r"/",          views.IndexHandler),
            (r"/lang/(.+)", views.LangHandler),
            (r"/dashboard", views.DashboardHandler),
            (r"/account",   views.AccountHandler),
            (r"/signup",    views.SignUpHandler),
            (r"/signin",    views.SignInHandler),
            (r"/signout",   views.SignOutHandler),
            (r"/passwd",    views.PasswdHandler),
            (r"/legal",     cyclone.web.RedirectHandler,
                                {"url": "/static/legal.txt"}),

            (r"/r/(.+)",  image.ImageResizeHandler),
            (r"/c/(.+)",  image.ImageResizeHandler, {'cmd' : 'crop'}),
            (r"/i/(.+)",  image.ImageHandler),
        ]

        # Initialize locales
        if "locale_path" in conf:
            cyclone.locale.load_gettext_translations(conf["locale_path"],
                                                     "images")

        # Set up database connections
        DatabaseMixin.setup(conf)

        # Set up imager processes
        ImagerMixin.setup(conf)

        conf["login_url"] = "/signin"
        conf["autoescape"] = None
        cyclone.web.Application.__init__(self, handlers, **conf)

class ProxyApplication(cyclone.web.Application):
    def __init__(self, config_file):
        conf = config.parse_config(config_file)
        handlers = [
            (r"/",      views.IndexHandler),
            (r"/(.+)",  proxy.DownloadHandler),
        ]

        # Set up database connections
        DatabaseMixin.setup(conf)

        cyclone.web.Application.__init__(self, handlers, **conf)
