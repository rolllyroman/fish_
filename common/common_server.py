# -*- coding:utf-8 -*-
#!/bin/python

"""
Author: $Author$
Date: $Date$
Revision: $Revision$

Description: Server factory
"""

from twisted.internet import reactor, threads

import consts
from log import log, LOG_LEVEL_RELEASE, LOG_LEVEL_ERROR
import net_resolver_pb
from server import Server
import redis_batch
import redis_instance

from common_db_define import *
from common.pb_utils import *
from common.db_utils import isServiceOutDate, userDBLogin, userDBLogout
from common.protocols.mahjong_consts import *
from datetime import datetime, date, timedelta
from common.logic.global_control import GlobalControl
from logic.fish_generator import FishGenerator
from logic.fish_array_generator import FishArrayGenerator
from common.i18n.i18n import initializeGame, isValidLang, getLangInst
from peer import Peer

import pickfish_pb2

import traceback
from redis.exceptions import RedisError
import time

import random
import math

import urllib2
import urllib
import socket
import xml.dom.minidom
from common.pyDes import des, PAD_PKCS5
import md5
import json
import copy
import re
import struct
import hot_write_pb2
from common.data.fish_levels import FISH_LEVELS_DATA

SERVICE_PROTOCOLS_INTERVAL_TICK = 1000 #刷新后台协议的轮询时间
SERVICE_STOP_SECS = 30 #还有人在服务器内等待的时间
# SERVICE_STOP_SECS = 10 #还有人在服务器内等待的时间
WAIT_END_SECS = 10 #全部玩家被T出后等待多久关闭服务器
#排行榜请求处理线程数
MAX_THREAD_FOR_RANK = 5
#排行榜1分钟才能请求刷一次
GET_RANK_INTERVAL_TICK = 60000
#排行榜刷新时间
RANK_REFRESH_TIMES = ['00:00', '06:00', '12:00', '18:00']
RANK_SAVE_TIME = 10 * 1000 #批量入库时间间隔

class CommonServer(Server):
    def __init__(self, *args, **kwargs):
        assert 'serviceTag' in kwargs
        self.serviceTag = kwargs['serviceTag']
        del kwargs['serviceTag']
        super(CommonServer, self).__init__(*args, **kwargs)
        self.ip = self.serviceTag.split(':')[1]
        self.port = self.serviceTag.split(':')[2]


    def startFactory(self):
        """
        启动完成才初始化数据
        """
        self.account2players = {}
        self.account2Sid = {}
        self.trialAccountPool = []
        self.trialAccountSet = []
        self.loginLocks = {}

        self.accountValidator = re.compile(r'^[a-zA-Z]\w{3,17}$')
        self.passwdValidator = re.compile(r'^.{8,20}$')

        redis = self.getPublicRedis()
        print '---------------------------- 2 --------------------------------------'
        '''
        while 1:
            try:
                redis.get(FORMAT_IP2CONTRYCODE)
            except RedisError, e:
                log('Wait for redis error[%s]'%(e))
                time.sleep(5)
            else:
                break
        '''
        print '---------------------------- 2.5 --------------------------------------'

        #需要初始化代理和房间号池
        hasRoom = redis.scard(GAME_ROOM_SET)
        # hasAgent = redis.hexists(FORMAT_ADMIN_ACCOUNT_TABLE%('CHNWX'), 'name')
        if not hasRoom:
            log('need init: room[%s]:[%s]'%('setRoomSet.py', hasRoom), LOG_LEVEL_RELEASE)
            e = None
            assert e

        serviceTag = self.serviceTag.split(':')
        self.ID = serviceTag[-1]
        del serviceTag[-1]
        self.serviceTag = ':'.join(serviceTag)
        print '---------------------------- 4 --------------------------------------'

        #load game config
        self.globalCtrl = GlobalControl(self)

        #鱼预生成，每种鱼生成1千条数据
        self.fishGenerator = FishGenerator()
        self.fishGenerator.load()
        self.fishArrayGenerator = FishArrayGenerator()
        self.fishArrayGenerator.load()

         #排行榜查询线程限制
        self.deferedsForRank = [None] * MAX_THREAD_FOR_RANK
        self.getRankQueue = []
        self.saveRankTimestamp = 0

        #关闭服务时间戳,时间戳为非0则不允许玩家连入游戏了
        #关闭阶段1:倒计时10秒断开所有玩家连接
        #关闭阶段2:30秒后关闭服务
        self.gameCloseTimestamp = 0
        self.tax_rate = 0
        self.isClosed = False
        self.isWaitEnd = False
        self.isEnding = False
        self.showFishHitCoiunt = False

        #读取服务信息时间戳
        self.lastResovledServiceProtocolsTimestamp = 0
        self.resovledServiceProtocolsLock = False

        #货币及相关代理彩池刷新
        self.currency, _, _ = self.serviceTag.split(':')
        self.currencyAgentCashRefreshTimestamp = 0

        initializeGame()

        self.table = FORMAT_GAME_SERVICE_TABLE%(self.ID, self.serviceTag)
        self.serviceProtocolTable = FORMAT_SERVICE_PROTOCOL_TABLE%(self.ID, self.serviceTag)
        pipe = redis.pipeline()
        pipe.hset(self.table, 'playerCount', 0)
        pipe.hset(self.table, 'roomCount', 0)
        pipe.delete(SERVER2ROOM%self.serviceTag)
        pipe.rpush(FORMAT_GAME_SERVICE_SET%(self.ID), self.table)

        #清空原服务器下的所有断线重连信息
        serverExitPlayer = SERVER_EXIT_PLAYER_FISH%(self.serviceTag, self.ID)
        if redis.exists(serverExitPlayer):
            exitPlayerList = redis.smembers(serverExitPlayer)
            for exitPlayer in exitPlayerList:
                if redis.exists(EXIT_PLAYER_FISH%(exitPlayer, self.ID)):
                    pipe.delete(EXIT_PLAYER_FISH%(exitPlayer, self.ID))
        pipe.delete(serverExitPlayer)
        pipe.execute()

        self.account2room = {}

    def loadFixedChannalData(self, redis, globalCtrl):
        max_player_count = redis.hget(FISH_ROOM_TABLE%(self.ID), 'max_player_count')
        globalCtrl.maxPlayerCount = int(max_player_count)

    def loadOtherChannalData(self, redis, globalCtrl):
        #房间配置
        room_name, base_coin, max_base_coin, step_base_coin, fish_need_count, fish_limit_count, max_add, min_add =\
                redis.hmget(FISH_ROOM_TABLE%(self.ID),\
                ('room_name', 'base_coin', 'max_base_coin', 'step_base_coin', 'fish_need_count', 'fish_limit_count', 'max_add', 'min_add'))
        globalCtrl.base_coin = int(base_coin)
        globalCtrl.max_base_coin = int(max_base_coin)
        globalCtrl.step_base_coin = int(step_base_coin)
        globalCtrl.roomName = room_name
        self.loadTaxRate(redis, globalCtrl)

        #任务配置
        globalCtrl.maxGetPrizeCount = -1
        globalCtrl.getNextPrizeAddCoin = -1
        globalCtrl.getPrizeCoinList = []

        #奖票配置
        # globalCtrl.bet2TicketRate = []
        pickTicketRate, pickTicketNeedCoin, ticketCoin, pickTicketGetRate, maxGetTicketCount, getTicketWaitTime = \
                redis.hmget(FISH_ROOM_TABLE%(self.ID),\
                ('rate', 'need_coin', 'coin_value', 'get_rate', 'max_ticket_count', 'ticket_wait_time'))
        try:
            globalCtrl.pickTicketRate = float(pickTicketRate)
        except:
            pass
        try:
            globalCtrl.pickTicketGetRate = float(pickTicketGetRate) / 100.00
        except:
            pass
        try:
            globalCtrl.pickTicketNeedCoin = int(pickTicketNeedCoin)
        except:
            globalCtrl.pickTicketNeedCoin = 0
        try:
            globalCtrl.ticketCoin = int(ticketCoin)
        except:
            globalCtrl.ticketCoin = 0
        try:
            globalCtrl.maxGetTicketCount = int(maxGetTicketCount)
        except:
            pass
        try:
            globalCtrl.getTicketWaitTime = eval(getTicketWaitTime)
        except:
            pass

        #鱼场设置
        try:
            globalCtrl.level2needCount = {}
            if fish_need_count:
                level2needCount = eval(fish_need_count)
                for level, needCount in level2needCount.iteritems():
                    globalCtrl.level2needCount[level-1] = needCount
        except:
            pass
        try:
            globalCtrl.level2limitCount = {}
            if fish_limit_count:
                level2limitCount = eval(fish_limit_count)
                for level, limitCount in level2limitCount.iteritems():
                    globalCtrl.level2limitCount[level-1] = limitCount
        except:
            pass
        try:
            globalCtrl.addFishMaxCount = int(max_add)
        except:
            pass
        try:
            globalCtrl.addFishMinCount = int(min_add)
        except:
            pass

    def loadChannalData(self, globalCtrl):
        redis = self.getPublicRedis()

        self.loadFixedChannalData(redis, globalCtrl)
        self.loadOtherChannalData(redis, globalCtrl)

    def loadTaxRate(self, redis, globalCtrl): #抽水
        taxRate = redis.hget(FISH_ROOM_TABLE%(self.ID), 'tax_rate')
        if not taxRate:
            taxRate = 0
        globalCtrl.oddsOfPumping = float(taxRate) / 100
        globalCtrl.reloadOdds()

    def getDate(self, refreshTime = '00:00'): #传入更新时间获得今日日期
        refreshHour, refreshMinute = refreshTime.split(':')
        nowTime = datetime.now().strftime("%H:%M")
        hour, minute = nowTime.split(':')
        if int(hour) < int(refreshHour) or (int(hour) == int(refreshHour) and int(minute) < int(refreshMinute)):
            return date.today() - timedelta(days=1)
        else:
            return date.today()

    def getRankData(self, refreshTimes = RANK_REFRESH_TIMES): #每日分时段排行榜用，获得当前时间所属的时段
        nowTimeData = time.localtime()
        nowTimestamp = time.mktime(nowTimeData)
        nowData = time.strftime('%Y-%m-%d', nowTimeData)
        timeList = []
        for hourStr in refreshTimes:
            timeStr = nowData + ' ' + hourStr + ':00'
            timestamp = time.mktime(time.strptime(timeStr,'%Y-%m-%d %H:%M:%S'))
            timeList.append(timestamp)
        getTimestamp = timeList[0]
        getIndex = 0
        print timeList
        if len(timeList) > 1:
            for index, timestamp in enumerate(timeList[1:]):
                if nowTimestamp > timestamp:
                    getTimestamp = timestamp
                    getIndex += 1
        return nowData + ' ' + refreshTimes[getIndex]

    def getGameModule(self, *initData):
        raise 'abstract interface'

    def isValidPacket(self, msgName):
        return True
    def cannonSkin(self, player, resp):
        "修改皮肤协议"
        try:
            print(u"查看修改的类型：%s , %s" % (resp.chair, resp.cannonType))
            player.cannonSkin = int(resp.cannonType)
            self.sendCannonSkin(player, resp)
        except Exceptiona as err:
            log(u'[try cannonSkin] skin Error %s' % err, LOG_LEVEL_ERROR)

    def sendCannonSkin(self, player, resp=None):
        "发送皮肤协议"
        try:
            if resp:
                chair = resp.chair
                cannonSkin = resp.cannonType
            else:
                chair = player.chair
                cannonSkin = player.cannonSkin

            rsp = pickfish_pb2.S_C_Cannon_skin()
            rsp.chair = chair
            rsp.cannonType = cannonSkin
            print(u"发送类型：%s , %s" % (player.chair, player.cannonSkin))
            print(rsp)
            player.game.sendAll(rsp)
        except Exception as err:
            log(u'[try sendCannonSkin] skin Error %s' % err, LOG_LEVEL_ERROR)
            traceback.print_exc()

    def hot_write(self, player, resp):

        print(u"开始更改内容: %s" % resp)
        if not player.game:
            return
        Aquatic = resp.Aquatic
        UnderWater = resp.UnderWater
        pump = resp.pump

        # 修改当前玩家的水上值
        if UnderWater:
            player.underWater = round(float(UnderWater), 2)
        if Aquatic:
            player.addChance = round(float(Aquatic), 2)
        if pump:
            player.game.pump = round(float(pump), 2)

        rsp = hot_write_pb2.S_C_Hot_write()
        rsp.UnderWater = player.underWater
        rsp.Aquatic = player.addChance
        rsp.pump = player.game.pump
        player.game.sendOne(player, rsp)

    def registerProtocolResolver(self):
        unpacker = net_resolver_pb.Unpacker
        self.recverMgr.registerCommands( (\
            unpacker(pickfish_pb2.C_S_CONNECTING, pickfish_pb2.C_S_Connecting, self.onReg), \
            unpacker(pickfish_pb2.C_S_FIRE, pickfish_pb2.C_S_Fire, self.onFire), \
            unpacker(pickfish_pb2.C_S_FISH_OUT, pickfish_pb2.C_S_FishOut, self.onFishOut), \
            unpacker(pickfish_pb2.C_S_HIT_FISH, pickfish_pb2.C_S_HitFish, self.onHitFish), \
            unpacker(pickfish_pb2.C_S_SWITCH_GUN, pickfish_pb2.C_S_SwitchGun, self.onSwitchGun), \
            unpacker(pickfish_pb2.C_S_LOCK_FISH, pickfish_pb2.C_S_LockFish, self.onLockFish), \
            unpacker(pickfish_pb2.C_S_EXIT_ROOM, pickfish_pb2.C_S_ExitRoom, self.onExit), \
            unpacker(pickfish_pb2.C_S_GOLD_TIME_COUNT, pickfish_pb2.C_S_GoldTimeCount, self.onGoldTimeCount), \
            unpacker(pickfish_pb2.C_S_PING, pickfish_pb2.C_S_Ping, self.onPing), \
            unpacker(pickfish_pb2.C_S_DEBUG_CONNECTING, pickfish_pb2.C_S_DebugConnecting, self.onDebugReg), \
            unpacker(pickfish_pb2.C_S_LOCK_FISH_START, pickfish_pb2.C_S_LockFishStart, self.onLockFishStart), \
            unpacker(pickfish_pb2.C_S_GET_RANK, pickfish_pb2.C_S_GetRank, self.onGetRank), \
            unpacker(pickfish_pb2.C_S_CANNON_SKIN, pickfish_pb2.C_S_Cannon_skin, self.cannonSkin), \
            unpacker(hot_write_pb2.C_S_HOT_WRITE, hot_write_pb2.C_S_Hot_write, self.hot_write), \
            ) )
        packer = net_resolver_pb.Packer
        self.senderMgr.registerCommands( (\
            packer(pickfish_pb2.S_C_TRY_REG_FAILED, pickfish_pb2.S_C_TryRegFailed), \
            packer(pickfish_pb2.S_C_JOIN_GAME_RESULT, pickfish_pb2.S_C_JoinGameResult, True), \
            packer(pickfish_pb2.S_C_JOIN_ROOM, pickfish_pb2.S_C_JoinRoom, True), \
            packer(pickfish_pb2.S_C_EXIT_GAME, pickfish_pb2.S_C_ExitGame), \
            packer(pickfish_pb2.S_C_FIRE, pickfish_pb2.S_C_Fire), \
            packer(pickfish_pb2.S_C_GENERATE_FISH, pickfish_pb2.S_C_GenerateFish, True), \
            packer(pickfish_pb2.S_C_PICK_FISH, pickfish_pb2.S_C_PickFish, True), \
            packer(pickfish_pb2.S_C_SWITCH_GUN, pickfish_pb2.S_C_SwitchGun), \
            packer(pickfish_pb2.S_C_CONNECTED, pickfish_pb2.S_C_Connected, True), \
            packer(pickfish_pb2.S_C_LOCK_FISH, pickfish_pb2.S_C_LockFish), \
            packer(pickfish_pb2.S_C_FISH_ARRAY, pickfish_pb2.S_C_FishArray, True), \
            packer(pickfish_pb2.S_C_NOTICE, pickfish_pb2.S_C_Notice), \
            packer(pickfish_pb2.S_C_GUN_TYPE_CHANGED, pickfish_pb2.S_C_GunTypeChanged), \
            packer(pickfish_pb2.S_C_DISCONNECTED, pickfish_pb2.S_C_Disconnected), \
            packer(pickfish_pb2.S_C_GOLD_TIME_RESULT, pickfish_pb2.S_C_GoldTimeResult), \
            packer(pickfish_pb2.S_C_PONG, pickfish_pb2.S_C_Pong), \
            packer(pickfish_pb2.S_C_COIN_REFRESH, pickfish_pb2.S_C_CoinRefresh), \
            packer(pickfish_pb2.S_C_FISH_HIT_COUNT, pickfish_pb2.S_C_FishHitCount), \
            packer(pickfish_pb2.S_C_LOCK_FISH_START, pickfish_pb2.S_C_LockFishStart), \
            packer(pickfish_pb2.S_C_RANK_INFO, pickfish_pb2.S_C_RankInfo, True), \
            packer(pickfish_pb2.S_C_ALL_FREEZING, pickfish_pb2.S_C_AllFreezing), \
            packer(pickfish_pb2.S_C_FREEZE_OVER, pickfish_pb2.S_C_FreezeOver), \
            packer(pickfish_pb2.S_C_CANNON_SKIN, pickfish_pb2.S_C_Cannon_skin), \
            packer(hot_write_pb2.S_C_HOT_WRITE, hot_write_pb2.S_C_Hot_write), \
        ) )
        self.registerServiceProtocols()

    def registerServiceProtocols(self):
        self.serviceProtoCalls = {
            HEAD_SERVICE_PROTOCOL_GAME_CLOSE.split('|')[0]              :       self.onServiceGameClose,
            HEAD_SERVICE_PROTOCOL_MEMBER_REFRESH.split('|')[0]          :       self.onServiceMemberRefresh,
            HEAD_SERVICE_PROTOCOL_AGENT_BROADCAST.split('|')[0]         :       self.onServiceAgentBroadcast,
            HEAD_SERVICE_PROTOCOL_OPERATOR_RESESSION.split('|')[0]      :       self.onServiceReSession,
            HEAD_SERVICE_PROTOCOL_KICK_MEMBER.split('|')[0]             :       self.onServiceKickMember,
            # HEAD_SERVICE_PROTOCOL_DISSOLVE_ROOM.split('|')[0]           :       self.onDissolvePlayerRoom,
            HEAD_SERVICE_PROTOCOL_KICK_MEMBER4REPEAT.split('|')[0]      :       self.onServiceKickMember4repeat,
            HEAD_SERVICE_PROTOCOL_GAME_CONFIG_REFRESH.split('|')[0]     :       self.onServiceGameConfigRefresh,
        }

    def onReg(self, player, req):
        session = req.sid
        log(u'[try reg] sid[%s].'%(req.sid), LOG_LEVEL_RELEASE)

        player.lang = getLangInst()
        respFailed = pickfish_pb2.S_C_Connected()
        respFailed.result = False

        redis = self.getPublicRedis()
        #关闭服务器中
        # if self.gameCloseTimestamp:
            # log(u'[try reg][error]closing server now.', LOG_LEVEL_RELEASE)
            # respFailed.reason = player.lang.MAINTAIN_TIPS
            # self.sendOne(player, respFailed)
            # errMsg = '服务器维护中'.decode('utf-8')
            # player.drop(errMsg)
            # return

        #是否存在转登录cache
        cacheTable = None
        cache = player.hashKey

        if cache in self.loginLocks:
            log(u'[try reg][error][%s] tryReg lock.'%(cache), LOG_LEVEL_RELEASE)
            return
        self.loginLocks[cache] = True

        #cache md5
        cacheTable = FORMAT_USER_HALL_SESSION%(req.sid)
        account, player.operatorSessionId, ip = redis.hmget(cacheTable, ('account', 'sid', 'loginIp'))
        if not account:
            # respFailed.reason = player.lang.LOGIN_TIPS_TIMEOUT
            # self.sendOne(player, respFailed)
            del self.loginLocks[cache]
            player.account = ""
            errorStr = "登录超时.".decode('utf-8')
            player.drop(errorStr, type = 2)
            return
        else:
            player.ip = ip
            player.descTxt = '%s:%s:%s'%(player.protoTag, player.ip, player.port)
            player.cacheTable = cacheTable

        #已登录或注册
        if player.account:
            log(u'[try reg][error]account[%s][%s] is already registered or logon.'%(player.account, account), LOG_LEVEL_RELEASE)
            respFailed.reason = player.lang.REG_TIPS_ALREADY_LOGON
            self.onExit(player)
            # self.sendOne(player, respFailed)
            # del self.loginLocks[cache]
            # player.drop("Already logon.", consts.DROP_REASON_INVALID, type = 2)
            # return

        if not account:
            log(u"[try reg][error]request account is empty.", LOG_LEVEL_RELEASE)
            respFailed.reason = player.lang.REG_TIPS_EMPTY_ACCOUNT_PASSWD
            self.sendOne(player, respFailed)
            del self.loginLocks[cache]
            player.drop("Empty account.", consts.DROP_REASON_INVALID)
            return

        #验证合法性
#        if not self.accountValidator.match(req.account):
#            log(u"[try reg][error]account invalid.")
#            if req.isLogin:
#                respFailed.reason = player.lang.LOGIN_TIPS_INVALID_ACCOUNT_PASSWD
#            else:
#                respFailed.reason = player.lang.REG_TIPS_INVALID_ACCOUNT
#            self.sendOne(player, respFailed)
#            del self.loginLocks[cache]
#            return
#
#        if not self.passwdValidator.match(req.passwd):
#            log(u"[try reg][error]passwd invalid.")
#            if req.isLogin:
#                respFailed.reason = player.lang.LOGIN_TIPS_INVALID_ACCOUNT_PASSWD
#            else:
#                respFailed.reason = player.lang.REG_TIPS_INVALID_PASSWD
#            self.sendOne(player, respFailed)
#            del self.loginLocks[cache]
#            return

        account2user_table = FORMAT_ACCOUNT2USER_TABLE%(account)
        table = redis.get(account2user_table)

        #已存在用户
        if table:
            player.loadDB(table, account = account)
            if player.valid != '1':
                log(u"[try login][error]account[%s] invalid."%(account), LOG_LEVEL_RELEASE)
                respFailed.reason = player.lang.LOGIN_TIPS_INVALID_ACCOUNT
                self.sendOne(player, respFailed)
                del self.loginLocks[cache]
                player.account = ""
                player.drop("Already freezen.", consts.DROP_REASON_INVALID)
                return

            if not cacheTable:
                log(u"[try reg][error]request passwd is empty.", LOG_LEVEL_RELEASE)
                respFailed.reason = player.lang.REG_TIPS_EMPTY_ACCOUNT_PASSWD
                self.sendOne(player, respFailed)
                del self.loginLocks[cache]
                player.account = ""
                player.drop("Password empty.", consts.DROP_REASON_INVALID)
                return

            if cacheTable:
                log(u'[try login for operator]operator[%s] cacheTable[%s] account[%s] sessionId[%s] ip[%s]'%\
                    (player.parentAg, cacheTable, player.account, player.operatorSessionId, ip), LOG_LEVEL_RELEASE)

            #账号已在线
            if account not in self.account2players and redis.sismember(ONLINE_ACCOUNTS_TABLE4FISH, account):
                log(u"[try login][error]account[%s] is in another server."%(account), LOG_LEVEL_RELEASE)
                player.account = ''
                player.drop("Kick for repeated login.", consts.DROP_REASON_REPEAT_LOGIN, type = 1)
                del self.loginLocks[cache]
                return
            if account in self.account2players:# or (redis.hget(table, 'online') == "1"):
                another = self.account2players[account]
                self.onExit(another)
                if account in self.account2Sid and session == self.account2Sid[account]:
                    another.drop("Kick for repeated login.", consts.DROP_REASON_REPEAT_LOGIN, type = 4)
                else:
                    another.drop("Kick for repeated login.", consts.DROP_REASON_REPEAT_LOGIN)
                player.loadDB(table)

#                log(u'[try login][error]account[%s] is already logon.'%(account))
#                respFailed.reason = player.lang.LOGIN_TIPS_ALREADY_LOGON
#                self.sendOne(player, respFailed)
#                del self.loginLocks[cache]
#                player.drop("Already online.", consts.DROP_REASON_INVALID)
#                return

            self.onTryRegSucceed(player, cache, False, session, '', -1)
        else:
            log(u"[try login][error]account[%s] is not existed."%(account), LOG_LEVEL_RELEASE)
            respFailed.reason = player.lang.LOGIN_TIPS_INVALID_ACCOUNT_PASSWD
            self.sendOne(player, respFailed)
            del self.loginLocks[cache]
            player.drop("Account is not exist.", consts.DROP_REASON_INVALID)
            return

    def onDebugReg(self, player, req):
        session = ''
        log(u'[try debug reg]account[%s] passwd[%s] mode[%s] action[%s] rule[%s] roomId[%s].'%\
                (req.account, req.passwd, req.mode, req.roomSetting.action, req.roomSetting.rule, req.roomSetting.roomid), LOG_LEVEL_RELEASE)

        if req.roomSetting.rule:
            rule = eval(req.roomSetting.rule)
            del rule[0]
            req.roomSetting.rule = str(rule)
        player.lang = getLangInst()
        respFailed = pickfish_pb2.S_C_Connected()
        respFailed.result = False

        redis = self.getPublicRedis()
        #关闭服务器中
        # if self.gameCloseTimestamp:
            # log(u'[try reg][error]closing server now.', LOG_LEVEL_RELEASE)
            # respFailed.reason = player.lang.MAINTAIN_TIPS
            # self.sendOne(player, respFailed)
            # player.drop("closing server now.", consts.DROP_REASON_INVALID)
            # return

        #是否存在转登录cache
        cacheTable = None
        cache = player.hashKey

        if cache in self.loginLocks:
            log(u'[try reg][error][%s] tryReg lock.'%(cache), LOG_LEVEL_RELEASE)
            return
        self.loginLocks[cache] = True

        #cache md5
        ip = player.descTxt.split(':')[1]
        account = req.account

        #已登录或注册
        if player.account:
            log(u'[try reg][error]account[%s][%s] is already registered or logon.'%(player.account, account), LOG_LEVEL_RELEASE)
            respFailed.reason = player.lang.REG_TIPS_ALREADY_LOGON
            self.onExit(player)
            # self.sendOne(player, respFailed)
            # del self.loginLocks[cache]
            # player.drop("Already logon.", consts.DROP_REASON_INVALID, type = 2)
            # return

        if not account:
            log(u"[try reg][error]request account is empty.", LOG_LEVEL_RELEASE)
            respFailed.reason = player.lang.REG_TIPS_EMPTY_ACCOUNT_PASSWD
            self.sendOne(player, respFailed)
            del self.loginLocks[cache]
            player.drop("Empty account.", consts.DROP_REASON_INVALID)
            return

        #验证合法性
#        if not self.accountValidator.match(req.account):
#            log(u"[try reg][error]account invalid.")
#            if req.isLogin:
#                respFailed.reason = player.lang.LOGIN_TIPS_INVALID_ACCOUNT_PASSWD
#            else:
#                respFailed.reason = player.lang.REG_TIPS_INVALID_ACCOUNT
#            self.sendOne(player, respFailed)
#            del self.loginLocks[cache]
#            return
#
#        if not self.passwdValidator.match(req.passwd):
#            log(u"[try reg][error]passwd invalid.")
#            if req.isLogin:
#                respFailed.reason = player.lang.LOGIN_TIPS_INVALID_ACCOUNT_PASSWD
#            else:
#                respFailed.reason = player.lang.REG_TIPS_INVALID_PASSWD
#            self.sendOne(player, respFailed)
#            del self.loginLocks[cache]
#            return

        account2user_table = FORMAT_ACCOUNT2USER_TABLE%(account)
        table = redis.get(account2user_table)

        #已存在用户
        if table:
            player.loadDB(table, account = account)
            if player.valid != '1':
                log(u"[try login][error]account[%s] invalid."%(account), LOG_LEVEL_RELEASE)
                respFailed.reason = player.lang.LOGIN_TIPS_INVALID_ACCOUNT
                self.sendOne(player, respFailed)
                del self.loginLocks[cache]
                player.account = ""
                player.drop("Already freezen.", consts.DROP_REASON_INVALID)
                return

            if not req.passwd:
                log(u"[try reg][error]request passwd is empty.", LOG_LEVEL_RELEASE)
                respFailed.reason = player.lang.REG_TIPS_EMPTY_ACCOUNT_PASSWD
                self.sendOne(player, respFailed)
                del self.loginLocks[cache]
                player.account = ""
                player.drop("Password empty.", consts.DROP_REASON_INVALID)
                return

            if player.passwd and player.passwd != md5.new(req.passwd).hexdigest():
                log(u"[try login][error]account[%s] password[%s]-[%s] invalid."%(req.account, player.passwd, req.passwd), LOG_LEVEL_RELEASE)
                respFailed.reason = player.lang.LOGIN_TIPS_INVALID_ACCOUNT_PASSWD
                self.sendOne(player, respFailed)
                del self.loginLocks[cache]
                player.account = ""
                player.drop("Password is not match.", consts.DROP_REASON_INVALID)
                return

            #账号已在线
            if account not in self.account2players and redis.sismember(ONLINE_ACCOUNTS_TABLE4FISH, account):
                log(u"[try login][error]account[%s] is in another server."%(account), LOG_LEVEL_RELEASE)
                player.account = ''
                player.drop("Kick for repeated login.", consts.DROP_REASON_REPEAT_LOGIN, type = 1)
                del self.loginLocks[cache]
                return
            if account in self.account2players:# or (redis.hget(table, 'online') == "1"):
                another = self.account2players[account]
                self.onExit(another)
                another.drop("Kick for repeated login.", consts.DROP_REASON_REPEAT_LOGIN)
                player.loadDB(table)

#                log(u'[try login][error]account[%s] is already logon.'%(account))
#                respFailed.reason = player.lang.LOGIN_TIPS_ALREADY_LOGON
#                self.sendOne(player, respFailed)
#                del self.loginLocks[cache]
#                player.drop("Already online.", consts.DROP_REASON_INVALID)
#                return

            self.onTryRegSucceed(player, cache, False, session, req.roomSetting, req.mode)
        else:
            log(u"[try login][error]account[%s] is not existed."%(account), LOG_LEVEL_RELEASE)
            respFailed.reason = player.lang.LOGIN_TIPS_INVALID_ACCOUNT_PASSWD
            self.sendOne(player, respFailed)
            del self.loginLocks[cache]
            player.drop("Account is not exist.", consts.DROP_REASON_INVALID)
            return

    def onRefreshRoomCards(self, player, req):
        if player.account not in self.account2players:
            return
        player.loadDB(player.table, isInit=False)
        # walletProto = pickfish_pb2.S_C_WalletMoney()
        # walletProto.roomCards = player.roomCards
        # walletProto.coin = player.coin
        # self.sendOne(player, walletProto)

    def onTryRegSucceed(self, player, cache, isReg, session, roomSetting, mode, isSendMsg = True):
        if cache in self.loginLocks:
            del self.loginLocks[cache]

        if not player or not player.hashKey:
            log(u"[try login][error]not found player hashKey.", LOG_LEVEL_RELEASE)
            return
        
        if session:
            self.account2Sid[player.account] = session

        redis = self.getPublicRedis()

        player.nickname = player.nickname.decode('utf-8')

        resp = pickfish_pb2.S_C_Connected()
        resp.result = True

        log(u"[try login]account[%s] login succeed, nickname[%s]."%(player.account, player.nickname), LOG_LEVEL_RELEASE)

        log(u"[try login]roomCards[%s] sex[%s]."%(player.roomCards, player.sex), LOG_LEVEL_RELEASE)

        self.account2players[player.account] = player

        self.userDBOnLogin(player, isReg)

        self.tryJoinGame(player, resp, isSendMsg)

    def tryJoinGame(self, player, resp, isSendMsg):
        if player.game:
            log(u'[try join game][error]account[%s] already in game.'%(player.account))
            return
        if player.account in self.account2room and self.account2room[player.account][0] in self.globalCtrl.num2game:
            _game = self.globalCtrl.num2game[self.account2room[player.account][0]]
        else:
            games = self.globalCtrl.getEmptyGames()
            if not games:
                _game = self.getGameModule(0, \
                        self.globalCtrl.maxPlayerCount, self)
                self.globalCtrl.addGame(_game, self.ID)
                _game.roomName = self.globalCtrl.roomName
                redis = self.getPublicRedis()
                pipe = redis.pipeline()
                pipe.hincrby(self.table, 'roomCount', 1)
                pipe.execute()
            else:
                _game = random.choice(games)
        _game.onJoinGame(player, resp, isSendMsg)

    def onPing(self, player, game):
        player.isOnline = True
        player.lastPingTimestamp = self.getTimestamp()
        resp = pickfish_pb2.S_C_Pong()
        self.sendOne(player, resp)
        
        log(u'[onPing]nickname[%s] isOnline[%s] lastOnlineState[%s]'%(player.nickname,player.isOnline,player.lastOnlineState), LOG_LEVEL_RELEASE)

    def onExitGame(self, player, req = None, sendMessage = True):
        if not player.game:
            log(u'[try exit game][error]nickname[%s] is not in game.'%(player.nickname), LOG_LEVEL_RELEASE)
            return

        byPlayer = False
        if req != None:
            log(u'[try exit game]exit by player.', LOG_LEVEL_RELEASE)
            byPlayer = True

        log(u'[try exit game]nickname[%s] room[%s].'%(player.nickname, player.game.roomId), LOG_LEVEL_RELEASE)
        player.game.onExitGame(player, sendMessage, byPlayer)

    def onModifyName(self, player, req):
        pass

    def onGMControl(self, player, req):
        if not player.game:
            log(u'[try control][error]nickname[%s] is not in game.'%(player.nickname), LOG_LEVEL_RELEASE)
            return

        errorMessage ={
            'packError':'命令格式错误'.decode(LANG_CODE),
            'gameError':'未加入游戏'.decode(LANG_CODE)
        }

        log(u'[try control]nickname[%s] want to control game.'%(player.nickname), LOG_LEVEL_RELEASE)
        if not player.isGM:
            log(u'[try control][error]nickname[%s] is not GM.'%(player.nickname), LOG_LEVEL_RELEASE)
            return
        commands = req.GMMessage.split(',')
        if not commands:
            self.sendGMErr(player,errorMessage['packError'])
            log(u'[try control][error]control failed, no command.', LOG_LEVEL_RELEASE)
            return
        for command in commands:
            try:
                type, data = command.split(':')
                # type, data = req.GMMessage.split(':')
            except:
                self.sendGMErr(player,errorMessage['packError'])
                log(u'[try control][error]control failed, nickname[%s] data[%s].'%(player.nickname, req.GMMessage), LOG_LEVEL_RELEASE)
                return
            
            player.game.onGMControl(player, int(type), data)
        # player.game.onGMControl(player, int(type), data)

    def sendGMErr(self, player, errMsg):
        resp = pickfish_pb2.S_C_GMControl()
        resp.result = False
        resp.reason = errMsg
        self.sendOne(player, resp)

    def onTalk(self, player, req):
        if not player.game:
            log(u'[try talk][error]nickname[%s] not in game.'%(player.nickname), LOG_LEVEL_RELEASE)
            return

        log(u'[try talk]nickname[%s] talk[%s] [%s] [%s].'%(player.nickname, req.emoticons, req.voice, req.duration), LOG_LEVEL_RELEASE)
        emoticons = req.emoticons
        side = player.chair
        voiceNum = req.voice
        voiceLen = req.duration
        player.game.onTalk(emoticons, side, voiceNum, voiceLen)

    def onDebugProto(self, player, req): #单客户端调试
        game = player.game
        side = req.selfSide

        # if game.roomId not in self.globalCtrl.num2game:
            # log(u'[on debug proto][error]account[%s] not in game.'%(player.account), LOG_LEVEL_RELEASE)
            # return

        if side >= game.maxPlayerCount or not game.players[side]:
            log(u'[on debug proto][error]side[%s] not in game[%s], maxPlayerCount[%s].'%(side, game.roomId, game.maxPlayerCount), LOG_LEVEL_RELEASE)
            return

        msgCode = req.msgCode
        protoData = struct.pack('>I', req.msgCode) + req.data
        log(u'[on debug proto]game[%s] side[%s] msgCode[%s].'%(game.roomId, side, msgCode), LOG_LEVEL_RELEASE)

        self.resolveMsg(game.players[side], protoData)

    def onSetGps(self, player, req): #发送gps信息
        if player.game:
            player.game.onSetGps(player, req.gpsValue)

    def onFire(self, player, req):
        if not player.game:
            log(u'[try fire][error] account[%s] is not in game.'%(player.account))
            return

        player.game.onFire(player, req.timestamp, req.dirX, req.dirY, req.bulletIds, req.gunType)

    def onFishOut(self, player, req):
        if not player.game:
            log(u'[try fish out][error] account[%s] is not in game.'%(player.account))
            return

        player.game.onFishOut(player, req.timestamp, req.fishIds)

    def onHitFish(self, player, req):
        if not player.game:
            log(u'[try hit fish][error] account[%s] is not in game.'%(player.account))
            return

        player.game.onHitFish(player, req.timestamp, req.bulletId, req.fishIds)

    def onSwitchGun(self, player, req):
        if not player.game:
            log(u'[try switch gun][error] account[%s] is not in game.'%(player.account), LOG_LEVEL_RELEASE)
            return

        player.game.onSwitchGun(player, req.upgrade)

    def onGetRank(self, player, req):
        """
        排行榜查询优化，线程池用完的情况下，将请求放入队列
        """
        return #暂时关闭
        _timestamp = self.getTimestamp()
        if req and _timestamp - player.lastGetRankTimestamp < GET_RANK_INTERVAL_TICK:
            player.invalidCounter('account[%s] refresh rank interval not enough.'%(player.account))
            return
        player.lastGetRankTimestamp = _timestamp
        try:
            threadIdx = self.deferedsForRank.index(None)
            self.deferedsForRank[threadIdx] = threads.deferToThread(self.getRankThread, threadIdx, player)
            self.deferedsForRank[threadIdx].addCallback(self.__onGetRankFinished)
        except ValueError:
            #是正常请求则排在队列尾部，否则插在最前（应该暂时不会存在此情况）
            if req:
                self.getRankQueue.append(player)
            else:
                self.getRankQueue.insert(0, player)

    def __onGetRankFinished(self, (threadIdx, player, resp)):
        """
        完成排行榜查询，包括可能的异常处理
        """
        if player and player.account:
            self.sendOne(player, resp)

        self.deferedsForRank[threadIdx] = None
        if self.getRankQueue:
            nextPlayer = self.getRankQueue.pop(0)
            self.onGetRank(nextPlayer, None)

    def getRankThread(self, threadIdx, selfPlayer):
        #已下线则忽略
        if not selfPlayer.account:
            return threadIdx, None, None

        redis = self.getPublicRedis()

        #获取盈利排行
        rankInfo = pickfish_pb2.S_C_RankInfo()
        rankInfo.rankForCoin.enabled = False
        rankInfo.rankForProfit.enabled = False
        rankInfo.rankForFish.enabled = False

        try:
            lastRank = RANK_COUNT-1
            lastPlayers = redis.zrevrange(FROMAT_USER_TICKETCOUNT_TABLE, lastRank, lastRank, True, int)
            if lastPlayers:
                lastPlayers = redis.zrevrangebyscore(FROMAT_USER_TICKETCOUNT_TABLE, lastPlayers[0][1], lastPlayers[0][1], score_cast_func = int)
                lastRank = redis.zrevrank(FROMAT_USER_TICKETCOUNT_TABLE, lastPlayers[0]) + len(lastPlayers) - 1
            players = redis.zrevrange(FROMAT_USER_TICKETCOUNT_TABLE, 0, lastRank, True, int)
            #更低排名玩家的还存不存在，不存在则屏蔽盈利0分玩家
            zeroPlayers = redis.zrevrangebyscore(FROMAT_USER_TICKETCOUNT_TABLE, 0, 0, score_cast_func = int)
            if zeroPlayers:
                less0Rank = redis.zrevrank(FROMAT_USER_TICKETCOUNT_TABLE, zeroPlayers[-1])
                less0RankPlayers = redis.zrevrange(FROMAT_USER_TICKETCOUNT_TABLE, less0Rank+1, less0Rank+1, False, int)
            else:
                less0RankPlayers = None

            rank = prevRank = 1
            sameCount = 0
            prevCoinDelta = players[0][1] if players else 0
            selfRank = 0
            for player in players:
                if player[1] >= prevCoinDelta:
                    rank = prevRank
                    sameCount += 1
                else:
                    rank = prevRank + sameCount
                    sameCount = 1
                prevRank = rank
                prevCoinDelta = player[1]
                playerAccount = player[0]
                playerTable = redis.get(FORMAT_ACCOUNT2USER_TABLE%(playerAccount))
                if playerAccount == selfPlayer.account:
                    selfRank = rank
                    pbAppendRank(rankInfo.rankForTicket.rankList, rank, redis.hget(playerTable, 'nickname'), player[1])
                else:
                    if player[1] or less0RankPlayers:
                        pbAppendRank(rankInfo.rankForTicket.rankList, rank, redis.hget(playerTable, 'nickname'), player[1])
            if not selfRank:
                selfTicketDelta = redis.zscore(FROMAT_USER_TICKETCOUNT_TABLE, selfPlayer.account)
                if not selfTicketDelta:
                    selfTicketDelta = 0
                else:
                    selfTicketDelta = int(selfTicketDelta)
                selfRankPlayers = redis.zrevrangebyscore(FROMAT_USER_TICKETCOUNT_TABLE, selfTicketDelta, selfTicketDelta, score_cast_func = int)
                if selfRankPlayers:
                    selfRank = redis.zrevrank(FROMAT_USER_TICKETCOUNT_TABLE, selfRankPlayers[0]) + 1
                else:
                    selfRank = rank + 1
                if selfRank > MY_MAX_RANK:
                    selfRank = NOT_RANK_USE_NUM
                pbAppendRank(rankInfo.rankForTicket.rankList, selfRank, selfPlayer.nickname, selfTicketDelta)
            rankInfo.rankForTicket.enabled = True
        except Exception, e:
            for tb in traceback.format_exc().splitlines():
                log(tb, LOG_LEVEL_ERROR)
            return threadIdx, None, None

        log(u'[try get rank]account[%s] get rank succeed.'%(selfPlayer.account))

        return threadIdx, selfPlayer, rankInfo

    def onLockFish(self, player, req):
        if not player.game:
            log(u'[try lock fish][error] account[%s] is not in game.'%(player.account), LOG_LEVEL_RELEASE)
            return

        player.game.onLockFish(player, req.timestamp, req.fishId, req.isLocked)

    def onLockFishStart(self, player, req):
        if not player.game:
            log(u'[try lock fish start][error] account[%s] is not in game.'%(player.account), LOG_LEVEL_RELEASE)
            return

        player.game.onLockFishStart(player)

    def onGoldTimeCount(self, player, req):
        if not player.game:
            log(u'[try gold time count][error] account[%s] is not in game.'%(player.account), LOG_LEVEL_RELEASE)
            return

        player.game.onGoldTimeCount(player, req.count)

    def savePlayerGameData(self, player, passwd):
        userOnlineTable = FORMAT_CUR_USER_GAME_ONLINE%(player.account)
        redis = self.getPublicRedis()
        redis.hset(userOnlineTable, 'game', self.ID)

    def removePlayerGameData(self, player):
        userOnlineTable = FORMAT_CUR_USER_GAME_ONLINE%(player.account)
        redis = self.getPublicRedis()
        redis.hdel(userOnlineTable, 'game')

    def saveSetStartData(self, game):
        if game.otherRoomTable:
            redis = self.getPublicRedis()
            accountList = []
            for player in game.getPlayers():
                accountList.append(player.account)
            accountsStr = ';'.join(accountList)
            redis.hmset(game.otherRoomTable,\
                {
                    'gameType':1,
                    'minNum':game.curGameCount,
                    'maxNum':game.gameTotalCount,
                    'accountList':accountsStr,
                }
            )

    def onExit(self, player, req = None):
        if not player.account:
            log(u'[try exit][error]account is null.', LOG_LEVEL_RELEASE)
            return

        #在游戏中
        if player.game:
            self.onExitGame(player, sendMessage = True)

        self.userDBOnLogout(player)

    def onRemoveGame(self, game):
        redis = self.getPublicRedis()
        # redis.delete(ROOM2SERVER%(game.roomId))
        # redis.srem(AG2SERVER%(game.parentAg), game.roomId)
        # redis.srem(SERVER2ROOM%(self.serviceTag), game.roomId)
        redis.hincrby(self.table, 'roomCount', -1)
        self.globalCtrl.removeGame(game)

    def userDBOnJoinGame(self, player, game):
        pass
        # redis = redis_instance.getInst(PUBLIC_DB)
        # pipe = redis.pipeline()
        # pipe.hset(ROOM2SERVER%(game.roomId), 'playerCount', game.playerCount)
        # if game.otherRoomTable:
            # pipe.hset(game.otherRoomTable, 'minNum', game.playerCount)
        # pipe.lpush(ROOM2ACCOUNT_LIST%(game.roomId), player.account)
        # pipe.execute()

    def userDBOnExitGame(self, player, game, isDrop):
        redis = redis_instance.getInst(PUBLIC_DB)
        pipe = redis.pipeline()
        if player.account in self.account2room:
            serverExitPlayer = SERVER_EXIT_PLAYER_FISH%(self.serviceTag, self.ID)
            exitPlayerData = EXIT_PLAYER_FISH%(player.account, self.ID)
            pipe.hmset(exitPlayerData,
                {
                    'ip'            :       self.ip,
                    'port'          :       self.port,
                    'game'          :       self.account2room[player.account][0],
                    'side'          :       self.account2room[player.account][1],
                }
            )
            pipe.sadd(serverExitPlayer, player.account)
            pipe.execute()

        if isDrop:
            # self.onExit(player)
            reactor.callLater(300, self.onDropTimeoutPlayer, player)

    def rmWaitRoom(self, account):
        del self.account2room[account]
        redis = redis_instance.getInst(PUBLIC_DB)
        pipe = redis.pipeline()
        serverExitPlayer = SERVER_EXIT_PLAYER_FISH%(self.serviceTag, self.ID)
        exitPlayerData = EXIT_PLAYER_FISH%(account, self.ID)
        pipe.delete(exitPlayerData)
        pipe.srem(serverExitPlayer, account)
        pipe.execute()

    def onDropTimeoutPlayer(self, player):
        if player in self.peerList[:]:
            player.drop('game end timeout', consts.DROP_REASON_INVALID, type = 2)

    def userDBOnLogin(self, player, reg = False):
        curTime = datetime.now()
        dateTimeStr = curTime.strftime("%Y-%m-%d %H:%M:%S")
        #本次登录session初始化
        player.sessionId = player.uid + curTime.strftime("%Y%m%d%H%M%S")
        player.loginTime = dateTimeStr
        redis = self.getPublicRedis()
        pipe = redis.pipeline()
        if reg:
            curDateStr = dateTimeStr.split(' ')[0]
            curRegDateTable = FORMAT_REG_DATE_TABLE%(curDateStr)
            pipe.sadd(curRegDateTable, player.account)
        userDBLogin(redis, pipe, player.account, self.ID, player.table, \
            player.descTxt, self.serviceTag, self.table, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), player.parentAg)

    def onFishLogout(self, pipe, player, dateTimeStr, redis): #退出捕鱼时需要记录的数据
        uid = player.uid
        agUid = player.parentAg
        curDateStr = dateTimeStr.split(' ')[0]
        totalBetCoin = player.totalBetCoin
        totalProfitCoin = player.totalProfitCoin
        totalWin = totalProfitCoin + totalBetCoin
        betDetail = str(player.betDetail)

        replayRedis = self.getPrivateRedis()
        replayNum = replayRedis.incr(PLAYER_REPLAY_NUM)
        replayPipe = replayRedis.pipeline()
        replayPipe.zadd(PLAYER_REPLAY_SET, betDetail, replayNum) #PLAYER_REPLAY_SET：回放集合
        replaySetLen = replayRedis.zcard(PLAYER_REPLAY_SET)
        if replaySetLen >= MAX_REPLAY_LEN:
            replayPipe.zremrangebyrank(PLAYER_REPLAY_SET, 0, (replaySetLen - MAX_REPLAY_LEN))
        replayPipe.execute()
        playerBetStr = {'bet':totalBetCoin, 'profit':totalProfitCoin, 'datetime': dateTimeStr, 'bet_id': replayNum,\
                'room_id':self.ID, 'uid': uid, 'ag':agUid, 'login_time':player.loginTime, 'init_coin':player.initCoin,\
                'add_coin':player.addCoin, 'add_ticket':player.addTicketCount, 'win':totalWin}

        # 存储玩家这次消耗的奖池
        player.curPrizePool = int(player.curPrizePool)
        if redis.exists(FISH_JACKPOT):
            if redis.hget(FISH_JACKPOT, self.ID):
                pipe.hincrby(FISH_JACKPOT, self.ID, player.curPrizePool)
            else:
                pipe.hset(FISH_JACKPOT, self.ID, player.curPrizePool)
        else:
            pipe.hset(FISH_JACKPOT, self.ID, player.curPrizePool)

        if redis.hget(FISH_JACKPOT_DIVIDED, self.ID):
            pipe.hincrbyfloat(FISH_JACKPOT_DIVIDED, self.ID, round(player.curDivied, 2))
        else:
            pipe.hset(FISH_JACKPOT_DIVIDED, self.ID, round(player.curDivied, 2))

        #玩家
        pipe.hincrbyfloat(player.table, 'coin', int(player.coin))
        pipe.hincrby(player.table, 'exchange_ticket', player.addTicketCount)
        pipe.hset(player.table, 'ticket_profit', player.totalProfitCoin4Ticket)
        pipe.hset(player.table, "cannonSkin", player.cannonSkin)
        pipe.set(FORMAT_USER_GAME_DATA_GOLD_TIME_COUNT%(player.account, self.ID), player.goldTimeCount)
        pipe.set(FORMAT_USER_GAME_DATA_GUN_COIN%(player.account, self.ID), player.gunCoin)
        # if player.addTicketCount:
            # pipe.zadd(FROMAT_USER_TICKETCOUNT_TABLE, player.account, player.ticketCount)
        self.saveRankData((player,))
        # pipe.set(PLAYER_DAY_LOCK_COUNT%(player.account, curDateStr), player.lockCount)
        # pipe.expire(PLAYER_DAY_LOCK_COUNT%(player.account, curDateStr), PLAYER_DAY_LOCK_COUNT_SAVE_TIME)

        log(u'[try logout]nickname[%s] goldTimeCount[%s] lockCount[%s] addTicketCount[%s] coin[%s].'\
                %(player.nickname, player.goldTimeCount, player.lockCount, player.addTicketCount, player.coin), LOG_LEVEL_RELEASE)

        pipe.hincrbyfloat(PLAYER_FISH_BET_DATA4ALL%uid, 'profit',totalProfitCoin)
        pipe.hincrbyfloat(PLAYER_FISH_BET_DATA4ALL%uid, 'bet', totalBetCoin)
        pipe.hincrbyfloat(PLAYER_FISH_BET_DATA4ALL%uid, 'win', totalWin)
        pipe.hincrbyfloat(PLAYER_FISH_BET_DATA4ALL%uid, 'ticket', player.addTicketCount)
        # pipe.hincrbyfloat(PLAYER_FISH_BET_DATA4DAY%(uid, curDateStr), 'profit', totalProfitCoin)
        # pipe.hincrbyfloat(PLAYER_FISH_BET_DATA4DAY%(uid, curDateStr), 'bet', totalBetCoin)
        pipe.hincrbyfloat(PLAYER_FISH_BET_DATA4DAY%(uid, curDateStr), 'ticket', player.addTicketCount)
        pipe.expire(PLAYER_FISH_BET_DATA4DAY%(uid, curDateStr), PLAYER_FISH_BET_DATA4DAY_SAVE_TIME)
        for _curDateStr, _totalBetCoin in player.dayAddBetData.iteritems():
            key = PLAYER_FISH_BET_DATA4DAY%(uid, _curDateStr)
            pipe.hincrbyfloat(key, 'bet', _totalBetCoin)
            pipe.hincrbyfloat(key, 'win', _totalBetCoin)
            pipe.expire(key, PLAYER_FISH_BET_DATA4DAY_SAVE_TIME)
        for _curDateStr, _totalProfitCoin in player.dayAddProfitData.iteritems():
            key = PLAYER_FISH_BET_DATA4DAY%(uid, _curDateStr)
            pipe.hincrbyfloat(key, 'profit', _totalProfitCoin)
            pipe.hincrbyfloat(key, 'win', _totalProfitCoin)
            pipe.expire(key, PLAYER_FISH_BET_DATA4DAY_SAVE_TIME)
        pipe.lpush(PLAYER_FISH_BET_DATA_DETAIL%uid, str(playerBetStr))
        pipe.ltrim(PLAYER_FISH_BET_DATA_DETAIL%uid, 0, PLAYER_FISH_BET_DATA_DETAILL_MAX_LEN)
        pipe.lpush(PLAYER_FISH_BET_DATA_DETAIL4DAY%(uid, curDateStr), str(playerBetStr))
        pipe.ltrim(PLAYER_FISH_BET_DATA_DETAIL4DAY%(uid, curDateStr), 0, PLAYER_FISH_BET_DATA_DETAIL4DAY_MAX_LEN)
        pipe.expire(PLAYER_FISH_BET_DATA_DETAIL4DAY%(uid, curDateStr), PLAYER_FISH_BET_DATA_DETAIL4DAY_SAVE_TIME)

        #代理
        agList = self.getAllFatherAg(agUid)
        for ag in agList:
            pipe.hincrbyfloat(AGENT_FISH_BET_DATA4ALL%ag, 'profit',totalProfitCoin)
            pipe.hincrbyfloat(AGENT_FISH_BET_DATA4ALL%ag, 'bet', totalBetCoin)
            pipe.hincrbyfloat(AGENT_FISH_BET_DATA4ALL%ag, 'win', totalWin)
            pipe.hincrbyfloat(AGENT_FISH_BET_DATA4ALL%ag, 'ticket', player.addTicketCount)
            # pipe.hincrbyfloat(AGENT_FISH_BET_DATA4DAY%(ag, curDateStr), 'profit', totalProfitCoin)
            # pipe.hincrbyfloat(AGENT_FISH_BET_DATA4DAY%(ag, curDateStr), 'bet', totalBetCoin)
            pipe.hincrbyfloat(AGENT_FISH_BET_DATA4DAY%(ag, curDateStr), 'ticket', player.addTicketCount)
            pipe.expire(AGENT_FISH_BET_DATA4DAY%(ag, curDateStr), AGENT_FISH_BET_DATA4DAY_SAVE_TIME)
            for _curDateStr, _totalBetCoin in player.dayAddBetData.iteritems():
                key = AGENT_FISH_BET_DATA4DAY%(ag, _curDateStr)
                pipe.hincrbyfloat(key, 'bet', _totalBetCoin)
                pipe.hincrbyfloat(key, 'win', _totalBetCoin)
                pipe.expire(key, AGENT_FISH_BET_DATA4DAY_SAVE_TIME)
            for _curDateStr, _totalProfitCoin in player.dayAddProfitData.iteritems():
                key = AGENT_FISH_BET_DATA4DAY%(ag, _curDateStr)
                pipe.hincrbyfloat(key, 'profit', _totalProfitCoin)
                pipe.hincrbyfloat(key, 'win', _totalProfitCoin)
                pipe.expire(key, AGENT_FISH_BET_DATA4DAY_SAVE_TIME)
            pipe.lpush(AGENT_FISH_BET_DATA_DETAIL%(ag, curDateStr), str(playerBetStr))
            pipe.ltrim(AGENT_FISH_BET_DATA_DETAIL%(ag, curDateStr), 0, AGENT_FISH_BET_DATA_DETAILL_MAX_LEN)
            pipe.expire(AGENT_FISH_BET_DATA_DETAIL%(ag, curDateStr), AGENT_FISH_BET_DATA_DETAIL_SAVE_TIME)

        #总
        pipe.hincrbyfloat(ALL_FISH_BET_DATA4ALL, 'profit',totalProfitCoin)
        pipe.hincrbyfloat(ALL_FISH_BET_DATA4ALL, 'bet', totalBetCoin)
        pipe.hincrbyfloat(ALL_FISH_BET_DATA4ALL, 'win', totalWin)
        pipe.hincrbyfloat(ALL_FISH_BET_DATA4ALL, 'ticket', player.addTicketCount)
        # pipe.hincrbyfloat(ALL_FISH_BET_DATA4DAY%(curDateStr), 'profit', totalProfitCoin)
        # pipe.hincrbyfloat(ALL_FISH_BET_DATA4DAY%(curDateStr), 'bet', totalBetCoin)
        pipe.hincrbyfloat(ALL_FISH_BET_DATA4DAY%(curDateStr), 'ticket', player.addTicketCount)
        pipe.expire(ALL_FISH_BET_DATA4DAY%(curDateStr), ALL_FISH_BET_DATA4DAY_SAVE_TIME)
        for _curDateStr, _totalBetCoin in player.dayAddBetData.iteritems():
            key = ALL_FISH_BET_DATA4DAY%(_curDateStr)
            pipe.hincrbyfloat(key, 'bet', _totalBetCoin)
            pipe.hincrbyfloat(key, 'win', _totalBetCoin)
            pipe.expire(key, ALL_FISH_BET_DATA4DAY_SAVE_TIME)
        for _curDateStr, _totalProfitCoin in player.dayAddProfitData.iteritems():
            key = ALL_FISH_BET_DATA4DAY%(_curDateStr)
            pipe.hincrbyfloat(key, 'profit', _totalProfitCoin)
            pipe.hincrbyfloat(key, 'win', _totalProfitCoin)
            pipe.expire(key, ALL_FISH_BET_DATA4DAY_SAVE_TIME)
        pipe.lpush(ALL_FISH_BET_DATA_DETAIL%(curDateStr), str(playerBetStr))
        pipe.ltrim(ALL_FISH_BET_DATA_DETAIL%(curDateStr), 0, ALL_FISH_BET_DATA_DETAILL_MAX_LEN)
        pipe.expire(ALL_FISH_BET_DATA_DETAIL%(curDateStr), ALL_FISH_BET_DATA_DETAILL_SAVE_TIME)

        #gameid
        pipe.hincrbyfloat(FISH_BET_DATA4ROOM%self.ID, 'profit',totalProfitCoin)
        pipe.hincrbyfloat(FISH_BET_DATA4ROOM%self.ID, 'bet', totalBetCoin)
        pipe.hincrbyfloat(FISH_BET_DATA4ROOM%self.ID, 'win', totalWin)
        pipe.hincrbyfloat(FISH_BET_DATA4ROOM%self.ID, 'ticket', player.addTicketCount)
        # pipe.hincrbyfloat(FISH_BET_DATA4DAY4ROOM%(self.ID, curDateStr), 'profit', totalProfitCoin)
        # pipe.hincrbyfloat(FISH_BET_DATA4DAY4ROOM%(self.ID, curDateStr), 'bet', totalBetCoin)
        pipe.hincrbyfloat(FISH_BET_DATA4DAY4ROOM%(self.ID, curDateStr), 'ticket', player.addTicketCount)
        pipe.expire(FISH_BET_DATA4DAY4ROOM%(self.ID, curDateStr), FISH_BET_DATA4DAY4ROOM_SAVE_TIME)
        for _curDateStr, _totalBetCoin in player.dayAddBetData.iteritems():
            key = FISH_BET_DATA4DAY4ROOM%(self.ID, _curDateStr)
            pipe.hincrbyfloat(key, 'bet', _totalBetCoin)
            pipe.hincrbyfloat(key, 'win', _totalBetCoin)
            pipe.expire(key, FISH_BET_DATA4DAY4ROOM_SAVE_TIME)
        for _curDateStr, _totalProfitCoin in player.dayAddProfitData.iteritems():
            key = FISH_BET_DATA4DAY4ROOM%(self.ID, _curDateStr)
            pipe.hincrbyfloat(key, 'profit', _totalProfitCoin)
            pipe.hincrbyfloat(key, 'win', _totalProfitCoin)
            pipe.expire(key, FISH_BET_DATA4DAY4ROOM_SAVE_TIME)
        pipe.lpush(FISH_BET_DATA_DETAIL4ROOM%(self.ID, curDateStr), str(playerBetStr))
        pipe.ltrim(FISH_BET_DATA_DETAIL4ROOM%(self.ID, curDateStr), 0, FISH_BET_DATA_DETAILL4ROOM_MAX_LEN)
        pipe.expire(FISH_BET_DATA_DETAIL4ROOM%(self.ID, curDateStr), FISH_BET_DATA_DETAILL4ROOM_SAVE_TIME)
        return pipe

    def userDBOnLogout(self, player):
        redis = self.getPublicRedis()
        curTime = datetime.now()
        dateTimeStr = curTime.strftime("%Y-%m-%d %H:%M:%S")
        playerSettingTable = FORMAT_ACCOUNT_SETTING_TABLE%(player.account, self.ID)
        pipe = redis.pipeline()

        self.removePlayerGameData(player)

        self.onFishLogout(pipe, player, dateTimeStr, redis)

        userDBLogout(pipe, player.account, self.ID, player.table, player.descTxt, self.table, dateTimeStr)

        key = EXIT_PLAYER_FISH%(player.account, self.ID)
        #退出数据清空，暂时在exitGame处理
        if player.account in self.account2players:
            del self.account2players[player.account]
        log(u'[try logout]nickname[%s] logout succeed.'%(player.nickname), LOG_LEVEL_RELEASE)
        player.account = ""

        log(u'[try logout]logout end, join again key[%s] result[%s].'%(key, redis.exists(key)), LOG_LEVEL_RELEASE)

    def onAddPeer(self, player):
        pass

    def onRemovePeer(self, player):
        if player.account:
            self.onExit(player)

    def closeServer(self):
        if not self.isClosed:
            #确保在线玩家先入库
            for player in self.account2players.values():
                self.onExit(player)

            #断线通知
            for peer in self.peerList[:]:
                peer.drop("close game server", consts.DROP_REASON_CLOSE_SERVER)

            reactor.callLater(SERVICE_STOP_SECS, reactor.stop)
            self.isClosed = True
        else:
            if not self.account2players:
                reactor.stop()

    def endAllGame(self):
        #确保在线玩家先入库
        for player in self.account2players.values():
            self.onExit(player)

        #断线通知
        for peer in self.peerList[:]:
            peer.drop("close game server", consts.DROP_REASON_CLOSE_SERVER, type = 2)

        reactor.callLater(WAIT_END_SECS, reactor.stop)

    def stopFactory(self):

        #清空游戏数据表
        redis = self.getPublicRedis()
        pipe = redis.pipeline()
        pipe.delete(self.table)
        serverExitPlayer = SERVER_EXIT_PLAYER_FISH%(self.serviceTag, self.ID)
        if redis.exists(serverExitPlayer):
            exitPlayerList = redis.smembers(serverExitPlayer)
            log(u'[on stop factory] exitPlayerList %s.'%(exitPlayerList), LOG_LEVEL_RELEASE)
            for exitPlayer in exitPlayerList:
                if redis.exists(EXIT_PLAYER_FISH%(exitPlayer, self.ID)):
                    pipe.delete(EXIT_PLAYER_FISH%(exitPlayer, self.ID))
        pipe.delete(serverExitPlayer)
        pipe.execute()
        pipe.execute()

        for peer in self.peerList[:]:
            try:
                redis.srem(ONLINE_ACCOUNTS_TABLE4FISH, peer.account)
            except:
                pass

    def onCheck(self, timestamp):
        super(CommonServer, self).onCheck(timestamp)
        # if isServiceOutDate():
            # log('on closeServer', LOG_LEVEL_RELEASE)
            # self.closeServer()

    def onRefresh(self, timestamp):
        super(CommonServer, self).onRefresh(timestamp)

        if not self.resovledServiceProtocolsLock and timestamp - self.lastResovledServiceProtocolsTimestamp >= SERVICE_PROTOCOLS_INTERVAL_TICK:
            self.resovledServiceProtocolsLock = True
            reactor.callInThread(self.readServiceProtocol, timestamp)
            self.lastResovledServiceProtocolsTimestamp = timestamp

        #定时同步所有货币流水
#        if not self.globalCtrl.currencyAgentCashRefreshLock and timestamp - self.currencyAgentCashRefreshTimestamp >= AGENT_CASH_REFRESH_TICK:
#            self.globalCtrl.currencyAgentCashRefreshLock = True
#            reactor.callInThread(self.globalCtrl.refreshCurrencyCash, self.currency)
#            self.currencyAgentCashRefreshTimestamp = timestamp

        if self.gameCloseTimestamp:
            if timestamp > self.gameCloseTimestamp:
                # log('on closeServer', LOG_LEVEL_RELEASE)
                self.closeServer()

        self.globalCtrl.tryPayout(timestamp, self.account2players)

        games = self.globalCtrl.getTickGames()
        for game in games:
            try:
                game.onTick(timestamp)
            except Exception as e:
                log('refresh error:%s'%(traceback.format_exc()), LOG_LEVEL_RELEASE)

        #排行榜定时入库
        if timestamp > self.saveRankTimestamp:
            self.saveRankData(self.account2players.itervalues())
            self.saveRankTimestamp = timestamp + RANK_SAVE_TIME

    def saveRankData(self, players): #排行榜入库
        redis = self.getPublicRedis()
        pipe = redis.pipeline()
        for player in players:
            tmpAllProfit = player.tmpAllProfit
            if not tmpAllProfit is None:
                pipe.zadd(FORMAT_USER_COINDELTA_TABLE, player.account, tmpAllProfit)
                player.tmpAllProfit = None
            tmpAllCoin = player.tmpAllCoin
            if not tmpAllCoin is None:
                pipe.zadd(FORMAT_USER_COIN_TABLE, player.account, tmpAllCoin)
                player.tmpAllCoin = None
        pipe.execute()

    def readServiceProtocol(self, timestamp):
        redis = self.getPublicRedis()

        protoName = redis.lpop(self.serviceProtocolTable)

        while protoName:
            log('protoName[%s]'%(protoName), LOG_LEVEL_RELEASE)
            protoArgs = protoName.split('|')
            if protoArgs:
                protoHead = protoArgs[0]
                if protoHead in self.serviceProtoCalls:
                    try:
                        self.serviceProtoCalls[protoHead](timestamp, *protoArgs[1:])
                    except:
                        for tb in traceback.format_exc().splitlines():
                            log(tb, LOG_LEVEL_ERROR)
            protoName = redis.lpop(self.serviceProtocolTable)

        self.resovledServiceProtocolsLock = False

    def onServiceGameClose(self, timestamp):
        #收到关闭服务器协议后就不允许新连接了
        redis = self.getPublicRedis()
        redis.lrem(FORMAT_GAME_SERVICE_SET%(self.ID), self.table)

        self.gameCloseTimestamp = timestamp + DEFAULT_CLOSE_GAME_TICK
        noticeProto = pickfish_pb2.S_C_Notice()
        noticeProto.repeatTimes = 2
        noticeProto.repeatInterval = 0
        noticeProto.id = 100000

        for player in self.account2players.itervalues():
            noticeProto.txt = player.lang.GAME_CLOSE_TIPS
            self.sendOne(player, noticeProto)

    def onServiceMemberRefresh(self, timestamp, memberAccount):
        if memberAccount in self.account2players:
            player = self.account2players[memberAccount]
            player.loadDB(player.table, isInit=False)
            if player.valid != '1':
                player.drop('account[%s] refresh to invalid.'%(player.account), consts.DROP_REASON_FREEZE)
                return
            #同步数据
            # walletProto = pickfish_pb2.S_C_WalletMoney()
            # walletProto.roomCards = player.roomCards
            # self.sendOne(player, walletProto)

    def onServiceAgentBroadcast(self, timestamp, ag, content, repeatTimes, repeatInterval, id):
        noticeProto = pickfish_pb2.S_C_Notice()
        noticeProto.repeatTimes = int(repeatTimes)
        noticeProto.repeatInterval = int(repeatInterval)
        noticeProto.txt = content.decode(LANG_CODE)
        noticeProto.id = int(id)
        parentAg = ag
        redis = self.getPublicRedis()
        if len(ag) == 1:
            self.sendAll(noticeProto)
        else:
            agList = self.getAllChild(parentAg)
            agList.append(parentAg)
            for player in self.account2players.values():
                if player.parentAg in agList and player.game and player.account not in player.game.exitPlayers:
                    self.sendOne(player, noticeProto)
        # self.send([player for player in self.account2players.itervalues() \
            # if isParentAg(redis, player.account, parentAg, player.table)], noticeProto)

    def getAllChild(self, ag):
        agList = []
        redis = self.getPublicRedis()
        childAgList = redis.smembers(AGENT_CHILD_TABLE%(ag))
        agList.extend(childAgList)
        if childAgList:
            for childAg in childAgList:
                agList.extend(self.getAllChild(childAg))
        return agList

    def getAllFatherAg(self, ag):
        agList = [ag]
        redis = self.getPublicRedis()
        faterAg = ag
        while True:
            faterAg = redis.get(AGENT2PARENT%(faterAg))
            if faterAg and len(faterAg) != 1:
                agList.append(faterAg) 
            else:
                break
        return agList

    def onServiceReSession(self, timestamp, account, sid):
        #第三方平台用户session刷新(一般用于同一账号二次登入)
        if account in self.account2players:
            player = self.account2players[account]
            if player.operatorSessionId != sid:
                player.operatorSessionId = sid
                player.drop('Kick for repeated login 3rd party.', consts.DROP_REASON_REPEAT_LOGIN)

    def onServiceKickMember(self, timestamp, memberAccount):
        """
        踢出指定玩家
        """
        if memberAccount in self.account2players:
            self.account2players[memberAccount].drop(\
                    'account[%s] is kicked by manager.'%(memberAccount), consts.DROP_REASON_INVALID)

    def onServiceKickMember4repeat(self, timestamp, memberAccount, sid):
        if memberAccount in self.account2players and self.account2players[memberAccount].operatorSessionId != sid:
            self.account2players[memberAccount].drop(\
                    'account[%s] is kicked by manager.'%(memberAccount), consts.DROP_REASON_REPEAT_LOGIN, type = 4)

    def onServiceGameConfigRefresh(self, timestamp):
        redis = self.getPublicRedis()
        self.loadOtherChannalData(redis, self.globalCtrl)

    def getPublicRedis(self):
        return redis_instance.getInst(PUBLIC_DB)

    def getPrivateRedis(self):
        try:
            publicRedis = self.getPublicRedis()
            redisIp, redisPort, redisNum, passwd = publicRedis.hmget(GAME2REDIS%(self.ID), ('ip', 'port', 'num', 'passwd'))
            import redis
            redisdb = redis.ConnectionPool(host=redisIp, port=int(redisPort), db=int(redisNum), password=passwd)
            return redis.Redis(connection_pool=redisdb)
        except Exception as e:
            log('[get private redis][error]message[%s]'%(e), LOG_LEVEL_RELEASE)
            return self.getPublicRedis()

    def sendOne(self, peer, protocol_obj):
        #test
        # print 'test sendOne:%s'%(protocol_obj.DESCRIPTOR.name), protocol_obj
        name = protocol_obj.__class__.__name__
        if peer.isControlByOne and protocol_obj.DESCRIPTOR.name != 'S_C_Disconnected':
            self.sendDebugProto(peer, protocol_obj)
            return
        if isinstance(peer.controlPlayer, Peer):
            super(CommonServer, self).sendOne(peer.controlPlayer, protocol_obj)
        elif isinstance(peer, Peer):
            super(CommonServer, self).sendOne(peer, protocol_obj)
        else:
            print 'File error, send'

    def send(self, peers, protocol_obj, excludes=()):
        #test
        # print 'test send:%s'%(protocol_obj.DESCRIPTOR.name), protocol_obj
        for peer in peers:
            if peer in excludes:
                continue
            if peer.isControlByOne:
                self.sendDebugProto(peer, protocol_obj)
            else:
                if isinstance(peer.controlPlayer, Peer):
                    self.sendData(peer.controlPlayer, self.senderMgr.pack(protocol_obj))
                elif isinstance(peer, Peer):
                    self.sendData(peer, self.senderMgr.pack(protocol_obj))
                else:
                    print 'File error, send'

    def sendDebugProto(self, player, protocol_obj):
        """
        发送调试模式协议
        """
        name = protocol_obj.__class__.__name__
        code = self.senderMgr._cmds[name].msg_code
        protoData = protocol_obj.SerializeToString()

        side = player.chair
        if player.chair < 0:
            side = 0

        controlPlayer = player.controlPlayer

        resp = pickfish_pb2.S_C_DebugProto()
        resp.selfSide = side
        resp.msgCode = code
        resp.data = protoData

        log(u'[send debug proto]controlPlayer[%s] side[%s] proto[%s].'%(controlPlayer.nickname, side, name), LOG_LEVEL_RELEASE)
        if controlPlayer.descTxt:
            self.sendData(controlPlayer, self.senderMgr.pack(resp))
        else:
            self.sendData(player, self.senderMgr.pack(resp))

    def saveGameTotalData(self, id, values):
        """
        记录游戏统计数据,id为需要记录的字段号，values为增加值 
        """
        redis = self.getPublicRedis()
        key = GAME_TOTAL_DATA%(self.ID)
        redis.hincrby(key, id, values)

