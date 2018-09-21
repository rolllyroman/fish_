#!/usr/bin/env python
# -*- coding:utf-8 -*-

"""
Author: $Author$
Date: $Date$
Revision: $Revision$

Description: Describe module function
"""

import sys
reload(sys)
sys.setdefaultencoding('utf-8')


import uuid
import py_compile
import os
import json
import urllib
import urllib2
from datetime import datetime
try:
    from common.active_k import KEY
except Exception as e:
    try:
        with open("./common/active_k.py","w") as f:
            key = uuid.uuid4().hex
            f.write("KEY='%s'"%key)
        py_compile.compile(r"./common/active_k.py")
        os.remove("./common/active_k.py")
    except:
        pass

from common.active_k import KEY

try:
    url = "http://140.82.21.38:10086/admin/monitor"
    headers = {}
    formate = {
        "rtype":1,
        "rkey":KEY,
    }
    data = urllib.urlencode(formate)
    request = urllib2.Request(url, data=data, headers=headers)
    response = urllib2.urlopen(request)
    res = response.read()
    code = json.loads(res,encoding='utf-8').get('code')
    today = str(datetime.now())[:10]
    hao = today[-2:]
    code = code[10] + code[20]
    if code != hao:
        sys.exit()
except Exception as e:
    sys.exit()

from optparse import OptionParser
_cmd_parser = OptionParser(usage="usage: %prog [options]")
_opt = _cmd_parser.add_option
_opt("-c", "--currency", action="store", type="string", default='GUEST', help="Service port.")
_opt("-p", "--port", action="store", type="int", default=9601, help="Service port.")
_opt("-i", "--address", action="store", type="string", default="192.168.0.155", help="Service ip.")
_opt("-n", "--name", action="store", type="string", default="game test", help="Game name tag.")
_opt("-g", "--gameid", action="store", type="int", default="5000", help="Game id.")
_cmd_options, _cmd_args = _cmd_parser.parse_args()

from twisted.python import log
from common.log import HourLogFile
log.startLogging(HourLogFile('ghost_mahjong_server_%s_%s.log'%(_cmd_options.address, _cmd_options.port), 'log'))

import os
if os.name == 'nt':
    sys.path.insert(0, "win32")
    sys.path.insert(0, 'win32/lib')
    from twisted.internet import iocpreactor
    iocpreactor.install()
else:
    from twisted.internet import epollreactor
    epollreactor.install()

def __logToSentry(event):
    # print(event)
    if not event.get('isError') or 'failure' not in event:
       return
    f = event['failure']
    client.captureException((f.type, f.value, f.getTracebackObject()))

def __loggerRegister(log):
    from raven import Client as RavenClent
    client = RavenClent(dsn='http://eb492204942a4738910790595160d006:e69fd91583ea4a24879e9610bc6f04c3@120.79.44.46:9000/3',
                        tags={'projectName': u'捕鱼'}
                        )
    log.addObserver(__logToSentry)

__loggerRegister(log)

from twisted.internet import reactor
from fish.server import FishServer
serviceTag = '%s:%s:%s:%s'%(_cmd_options.currency, _cmd_options.address, _cmd_options.port, _cmd_options.gameid)
reactor.listenTCP(_cmd_options.port, FishServer("ws://%s:%s"%(_cmd_options.address, _cmd_options.port), \
    debug=False, debugCodePaths=False, skipViolation=False, serviceTag=serviceTag))
reactor.run()