# -*- coding:utf-8 -*-
#!/bin/python

"""
Author: $Author$
Date: $Date$
Revision: $Revision$

Description: Player peer
"""

from common.log import log, LOG_LEVEL_RELEASE
from common.peer import Peer
from common import consts
from common.pickfish_pb2 import S_C_Disconnected, S_C_CoinRefresh
from common_db_define import *
from common.protocols.mahjong_consts import *
import redis_instance

import time
from datetime import datetime
import copy

SESSION_TIMEOUT_TICK = 300000
GAME_KICK_OUT_TICK = 30 * 1000

DROP_REASON_CODE2TXT = {
    consts.DROP_REASON_INVALID      :   "与服务器的连接中断。".decode(LANG_CODE),
    consts.DROP_REASON_TIMEOUT      :   "你因长时间未做操作，被断开连接，请重新登录。".decode(LANG_CODE),
    consts.DROP_REASON_FREEZE       :   "你的账号已被管理员冻结，请咨询客服了解详请。".decode(LANG_CODE),
    consts.DROP_REASON_CLOSE_SERVER :   "系统因进行维护暂已关闭，请稍后再进。".decode(LANG_CODE),
    consts.DROP_REASON_REPEAT_LOGIN :   "你的账号已从其它位置登录，请咨询客服了解详情。".decode(LANG_CODE),
}

class CommonPlayer(Peer):
    def __init__(self):
        super(CommonPlayer, self).__init__()

        self.game = None
        self.endType = None
        self.chair = consts.SIDE_UNKNOWN
        self.isControlByOne = False

        self.uid = 0
        self.account = ""
        self.passwd = ""
        self.nickname = ""
        self.money = 0
        self.coin = 0
        self.initCoin = 0
        self.addCoin = 0
        self.parentAg = ''
        self.sex = 0
        self.roomCards = 0
        self.headImgUrl = ''
        self.region = ''
        self.valid = '1'
        self.isGM = False
        # 总分数
        self.totalGameScore = 0
        self.maxScore = 1

        #微信
        self.openID = None
        self.refreshToken = None
        self.accessToken = None
        self.unionID = None

        self.table = ''

        #用户sessionId
        self.operatorSessionId = ""
        #本次登录session
        self.sessionId = ""
        self.cacheTable = ''

        self.lastSessionTimestamp = int(time.time()*1000)
        self.lastGetRankTimestamp = 0
        self.gameLastPacketTimestamp = 0
        self.loginTime = 0

        # 玩家在线状态相关参数
        self.lastPingTimestamp = int(time.time()*1000)
        self.lastOnlineState = False
        self.isOnline = True

        self.totalGameScore = 0
        #投注及得分信息缓存
        self.betCoin = 0
        self.profitCoin = 0
        self.totalBetCoin = 0
        self.totalProfitCoin = 0
        self.oldCoinDelta = 0
        self.oldMostHighFishLevel = self.mostHighFishLevel = 0
        self.oldMostHighFishCount = self.mostHighFishCount = 0
        self.isBetInfoDBCommiting = False
        self.coinDelta = 0
        self.coinRunning = 0
        self.taxCoin = 0

        #奖票
        self.addTicketCount = 0
        self.ticketCount = 0
        self.totalProfitCoin4Ticket = 0
        self.nextGetTicketTimestamp = 0


        #奖池
        self.curPrizePool = 0 # 用户当前的奖池
        self.curDivied = 0

        # 炮类型
        self.cannonSkin = 0

    def loadDB(self, playerTable, isInit=True, account = None):
        #配置信息
        redis = redis_instance.getInst(PUBLIC_DB)

        if isInit:
            self.table = playerTable
            self.uid = self.table.split(':')[-1]
            self.account, self.passwd, self.nickname, self.money, self.parentAg, self.currency,\
                    self.valid, self.sex, self.headImgUrl, self.maxScore, self.coin, self.ticketCount,\
                    self.totalProfitCoin4Ticket, self.cannonSkin = redis.hmget(playerTable,\
                    ('account', 'password', 'nickname', 'money', 'parentAg',\
                    'currency', 'valid', 'sex', 'headImgUrl', 'maxScore', 'coin', 'exchange_ticket', 'ticket_profit', 'cannonSkin'))

            try:
                self.coin = int(float(self.coin))
            except:
                self.coin = 0
            try:
                self.ticketCount = int(self.ticketCount)
            except:
                self.ticketCount = 0
            try:
                self.totalProfitCoin4Ticket = int(self.totalProfitCoin4Ticket)
            except:
                self.totalProfitCoin4Ticket = 0
            self.coin, self.money = int(self.coin), round(float(self.money), 2)
            self.initCoin = self.coin
            redis.hincrbyfloat(playerTable, 'coin', -self.coin)
            # self.coin = 99999
            self.sex = int(self.sex) if self.sex else 0
            self.maxScore = int(self.maxScore) if self.maxScore and int(self.maxScore) >= 1 else 1
            self.headImgUrl = self.headImgUrl if self.headImgUrl else ''
            self.isGM = bool(int(redis.sismember(GM_SET, self.account)))

            roomCards = redis.get(USER4AGENT_CARD%(self.parentAg, self.uid))
            if roomCards and int(roomCards) > 0:
                self.roomCards = int(roomCards)
            else:
                self.roomCards = 0
            try:
                self.nickname = self.nickname.decode('utf-8')
            except:
                pass

            self.cannonSkin = int(self.cannonSkin) if self.cannonSkin else 0

        else:
            self.passwd, self.money, self.valid, self.sex, self.headImgUrl, coin, self.cannonSkin = redis.hmget(playerTable, ('password', 'money', 'valid', 'sex', 'headImgUrl', 'coin', 'cannonSkin'))

            coin = int(coin)
            self.coin += coin
            self.addCoin += coin
            redis.hincrbyfloat(playerTable, 'coin', -coin)
            if self.game:
                coinRefresh = S_C_CoinRefresh()
                coinRefresh.side = self.chair
                coinRefresh.deltaCoin = coin
                self.game.sendExclude((self,), coinRefresh)

            self.sex = int(self.sex) if self.sex else 0
            self.headImgUrl = self.headImgUrl if self.headImgUrl else ''

            roomCards = redis.get(USER4AGENT_CARD%(self.parentAg, self.uid))
            if roomCards and int(roomCards) > 0:
                self.roomCards = int(roomCards)
            else:
                self.roomCards = 0
            self.cannonSkin = int(self.cannonSkin) if self.cannonSkin else 0

    def isSessionTimeout(self, timestamp):
        return timestamp - self.lastSessionTimestamp > SESSION_TIMEOUT_TICK

    def isGameTimeout(self, timestamp):
        return timestamp - self.gameLastPacketTimestamp > GAME_KICK_OUT_TICK

    def onCheck(self, timestamp):
        if not super(CommonPlayer, self).onCheck(timestamp):
            return False
        return True

    def drop(self, reason, reasonCode = None, type = 2):
        resp = S_C_Disconnected()
        resp.actionType = type
        if reasonCode in DROP_REASON_CODE2TXT:
            resp.reason = DROP_REASON_CODE2TXT[reasonCode]
        else:
            resp.reason = reason
        if type != 4:
            try:
                self.factory.sendOne(self, resp)
            except:
                pass
        super(CommonPlayer, self).drop(reason, reasonCode)

    def onMessage(self, payload, isBinary):
        super(CommonPlayer, self).onMessage(payload, isBinary)
        self.lastPacketTimestamp = self.factory.getTimestamp()
        self.gameLastPacketTimestamp = self.factory.getTimestamp()

