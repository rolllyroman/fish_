# -*- coding:utf-8 -*-
#!/bin/python

"""
Author: $Author$
Date: $Date$
Revision: $Revision$

Description: Server factory
"""

from common.common_server import CommonServer
from common.log import log, LOG_LEVEL_RELEASE, LOG_LEVEL_ERROR
from common import net_resolver_pb
from common.protocols.mahjong_consts import *

from player import Player
from game import Game

from db_define import *
from common.common_db_define import *

import redis_instance

import copy
import time

class FishServer(CommonServer):
    protocol = Player

    def __init__(self, *args, **kwargs):
        super(FishServer, self).__init__(*args, **kwargs)

    def getGameModule(self, *initData):
        return Game(*initData)

    def registerProtocolResolver(self):

        super(FishServer, self).registerProtocolResolver()

    def doAfterRefresh(self, player):
        '''
        刷新数据结束后操作
        '''
        super(FishServer, self).doAfterRefresh(player)

    def saveLockFishData(self, player):
        redis = self.getPublicRedis()
        player.lockCount -= 1
        curDateStr = self.getDate()
        pipe = redis.pipeline()
        # pipe.incrby(PLAYER_DAY_LOCK_COUNT%(player.account, curDateStr), -1)
        # pipe.expire(PLAYER_DAY_LOCK_COUNT%(player.account, curDateStr), PLAYER_DAY_LOCK_COUNT_SAVE_TIME)
        pipe.hincrby(player.table, 'lockCount', -1)
        pipe.execute()


    def getRedPickFishNumber(self):
        " 获取红包数量 "
        redis = self.getPublicRedis()
        timestamp = time.strftime("%Y-%m-%d", time.localtime())
        number = redis.get("fish:redpick:fish:%s:number" % timestamp) or 0
        del redis
        return int(number)

    def setRedPickFishNumber(self, player):
        " 设置红包数量 "
        redis = self.getPublicRedis()
        timestamp = time.strftime("%Y-%m-%d", time.localtime())
        # 记录每天捕获的红包鱼数量
        redis.incrby("fish:redpick:fish:%s:number" % timestamp, 1)
        # 记录每个玩家捕获的红包鱼数量
        redis.hincrby("fish:redpick:account:hesh", player.account, 2)




