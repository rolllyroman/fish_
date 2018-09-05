#!/usr/bin/env python
# -*- coding:utf-8 -*-

"""
@Author: $Author$
@Date: $Date$
@version: $Revision$

Description: Describe module function
"""

from common.gameobject import GameObject
from common import consts
from common.consts import ERR_MSG
from common.log import log, LOG_LEVEL_RELEASE
from common_player import CommonPlayer

from common.protocols.mahjong_consts import *
from common_db_define import *

from common import pickfish_pb2
from common.pb_utils import *
import random
import time
from datetime import datetime
import copy
import redis_instance
import re

WAIT_BACK_TIME = 15*1000 + consts.LAG_MS
WAIT_DISSOLVE_TIME = 3 * 60 * 1000 #等待解散时间
GAME_NOT_START_END_TIME = 6 * 60 * 60 * 1000
PUBLIC_ROOM_GAME_NOT_START_END_TIME = 5 * 60 * 1000
OTHER_TYPE_GAME_NOT_START_END_TIME = 6 * 60 * 60 * 1000

PING_INTERVAL_TICK = 5*1000
WAIT_JOIN_TIME = 20 * 1000

class CommonGame(GameObject):
    """
    """
    def __init__(self, desk, maxPlayerPerDesk, server, ruleParams = ''):
        """
        """
        self.roomId = server.ID
        self.server = server
        self.roomName = ''
        self.parentAg = None
        self.playerCount = 0
        self.maxPlayerCount = maxPlayerPerDesk
        self.curGameCount = 0
        self.gamePlayedCount = 0
        self.players = [None]*self.maxPlayerCount
        self.side2gps = {}
        self.dealer = None
        self.controlPlayerSide = -1 #调试模式时可能指定由一个人控制四个人
        self.dealerCount = 0
        self.specialTile = None
        self.isDebug = False
        self.isParty = False
        self.ownner = ''
        self.otherRoomTable = ''
        self.isUseRoomCards = False
        self.needRoomCards = 1
        self.baseScore = 1 #基本分
        self.isSendReadyHand = False
        self.isHidden = False
        #倒计时回调及毫秒
        self.stage = WAIT_START #游戏状态
        self.exitPlayers = [] #掉线玩家的位置列表
        self.countPlayerSides = []
        self.ready2NextGameSides = []

        #时间记录
        self.gameStartTime = 0
        self.gameEndTime = 0

        self.waitChairs = []
        self.waitChair2time = {}
        self.waitChair2Account = {}

        self.ruleDescs = []
        self.initByRuleParams([])

        self.resetSetData()

        # 总奖池
        self.PrizePool = 0


#++++++++++++++++++++ 响应消息回调 ++++++++++++++++++++

    def onSetGps(self, player, gpsValue):
        """
        设置gps
        """
        self.side2gps[player.chair]=gpsValue

        resp = pickfish_pb2.S_C_Gps()
        for side, gps in self.side2gps.items():            
            gpsData = resp.gpsDatas.add()
            gpsData.chair = side
            gpsData.gpsValue = gps
        self.sendAll(resp)

    def onJoinGame(self, player, resp, isSendMsg):
        server = self.server
        roomId = self.roomId
        if player.account in server.account2room and roomId == server.account2room[player.account][0]:
            chair = server.account2room[player.account][1]
        else:
            chair = self.getEmptyChair()
            if chair == consts.SIDE_UNKNOWN:
                return
        player.chair = chair
        player.game = self
        #reset
        player.resetGoldTime()

        server.savePlayerGameData(player, roomId)
        self.playerCount += 1
        self.players[chair] = player

        joinResponse = pickfish_pb2.S_C_JoinRoom()
        pbPlayerInfo(joinResponse.info, self, player.chair)
        pbRoomInfo(resp.myInfo.roomInfo, server, self)
        pbPlayerInfo(resp.myInfo.selfInfo, self, player.chair, isNeedMyData = True)
        for p in self.players:
            if not p:
                continue
            _playerInfo = resp.myInfo.roomInfo.playerList.add()
            pbPlayerInfo(_playerInfo, self, p.chair)
            
        if isSendMsg:
            self.sendOne(player, resp)
            self.sendExclude((player,), joinResponse)

        server.userDBOnJoinGame(player, self)

        # 发送炮类型信息
        for _player in player.game.getPlayers():
            server.sendCannonSkin(_player)

        self.doAfterJoinGame(player, isSendMsg)

    def doAfterJoinGame(self, player, isSendMsg):
        pass

    def onExitGame(self, player, sendMessage = True, byPlayer = False, isEndGame = False):
        """
        退出游戏
        """
        if not player or not player.game or player.game != self:
            return

        isDrop = True #是否断开玩家，只有离开当前game时才为true
        side = player.chair
        log(u'[on exit]nickname[%s] is exit room[%s] in wait time.'%(player.nickname, self.roomId), LOG_LEVEL_RELEASE)
        if sendMessage:
            exitResp = pickfish_pb2.S_C_ExitGame()
            exitResp.info.side = side
            exitResp.info.nickname = player.nickname
            self.sendExclude((player,), exitResp)
        self.players[side] = None
        self.playerCount -= 1
        self.bulletMgr.destroyByPlayer(player)
        if player.chair not in self.waitChairs:
            self.waitChairs.append(player.chair)
        self.waitChair2time[player.chair] = self.server.getTimestamp() + WAIT_JOIN_TIME
        self.server.account2room[player.account] = (self.roomId, player.chair)
        self.waitChair2Account[player.chair] = player.account
        player.chair = consts.SIDE_UNKNOWN
        player.game = None

        self.server.userDBOnExitGame(player, self, isDrop)
        if self.playerCount <= 0 and not self.waitChairs:
            self.destroy()
            self.server.onRemoveGame(self)

    def onTalk(self, emoticons, side, voiceNum, duration): #发表情和语音
        log(u'[player talk]room[%s] side[%s] talk[%s] [%s] [%s].'%(self.roomId, side, emoticons, voiceNum, duration), LOG_LEVEL_RELEASE)
        resp = pickfish_pb2.S_C_Talk()
        resp.talkSide = side
        if emoticons:
            resp.emoticons = emoticons
        if voiceNum:
            resp.voice = voiceNum
        if duration:
            resp.duration = duration
        # self.sendExclude((self.players[side],), resp)
        self.sendAll(resp)

#++++++++++++++++++++ 响应消息回调 end ++++++++++++++++++++

#++++++++++++++++++++ 工具函数 ++++++++++++++++++++
    def removeRoom(self):
        for player in self.getPlayers():
            self.onExitGame(player, isEndGame = True, sendMessage = False)
        if self.playerCount <= 0: #房间无人则移除房间
            log(u'[try end game] nobody in room[%s].'%(self.roomId), LOG_LEVEL_RELEASE)
            self.server.onRemoveGame(self)
        else:
            log(u'[try end game][error]player in room[%s], players[%s], playerCount[%s]'%(self.roomId, self.getPlayers(), self.playerCount), LOG_LEVEL_RELEASE)

    def resetSetData(self):
        '''
        每局数据初始化
        '''
        self.setStartTime = 0
        self.setEndTime = 0
        for player in self.getPlayers():
            player.resetPerGame()

        #回放
        self.replayData = []
        self.replayinitTilesData = []

        self.dicePoints = []
        self.lastDiscard = ''
        self.lastDiscardSide = -1
        self.curPlayerSide = 0
        self.lastOperateSide = -1
        self.beGrabKongHuPlayer = None

#++++++++++++++++++++ 通用麻将工具函数 end ++++++++++++++++++++

#++++++++++++++++++++ 通用房间服务工具 ++++++++++++++++++++
    def sendOne(self, player, protocol_obj):
        if player.chair not in self.exitPlayers:
            log(u'[try send]account[%s]'%(player.nickname), LOG_LEVEL_RELEASE)
            self.server.sendOne(player, protocol_obj)

    def sendExclude(self, excludePlayers, protocol_obj):
        log(u'[try send]game[%s] exit player %s'%(self.roomId, self.exitPlayers), LOG_LEVEL_RELEASE)
        self.server.send(self.getOnlinePlayers(excludePlayers), protocol_obj)

    def sendAll(self, protocol_obj):
        log(u'[try send]game[%s] exit player %s'%(self.roomId, self.exitPlayers), LOG_LEVEL_RELEASE)
        self.server.send(self.getOnlinePlayers(), protocol_obj)

    def getEmptyChair(self):
        """
        return an empty side range[0:maxPlayerCount-1]
        return -1 for full
        """
        for chair, player in enumerate(self.players):
            if not player:
                if chair in self.waitChairs:
                    continue
                return chair

        return consts.SIDE_UNKNOWN

    def getOnlinePlayers(self, excludePlayers=()):
        return [player for player in self.players if (player and player not in excludePlayers and player.chair not in self.exitPlayers)]

    def getPlayers(self, excludePlayers=()):
        return [player for player in self.players if (player and player not in excludePlayers)]

    def getPlayers2sides(self, players = ()):
        sides = []
        for player in players:
            sides.append(player.chair)
        return sides

    def onTick(self, timestamp):
        """
        房间服务心跳
        """
        for chair, waitTime in self.waitChair2time.items():
            if timestamp > waitTime:
                self.waitChairs.remove(chair)
                del self.waitChair2time[chair]
                account = self.waitChair2Account[chair]
                self.server.rmWaitRoom(account)
        if self.playerCount <= 0 and not self.waitChairs:
            self.destroy()
            self.server.onRemoveGame(self)

#++++++++++++++++++++ 通用房间服务工具 end ++++++++++++++++++++

#++++++++++++++++++++ 房间服务可重写接口 ++++++++++++++++++++

    def initByRuleParams(self, ruleParams):
        """
        Abstract interface for parse rule parameters
        """
        if not ruleParams:
            self.ruleDescs = ''
            return
        params = eval(ruleParams)

        totalCount = int(params[-3])
        if totalCount:
            self.gameTotalCount = totalCount
            self.ruleDescs.append("%s局"%(self.gameTotalCount))

        self.needRoomCards = int(params[-2])
        self.baseScore = max(int(params[-1]), 1)
        self.ruleDescs.append("底分%s"%(self.baseScore))

        self.ruleDescs = "-".join(self.ruleDescs).decode('utf-8')

        log(u'[get gameRules]room[%s] ruleParams[%s] ruleTxt[%s]'%(self.roomId, params, self.ruleDescs),LOG_LEVEL_RELEASE)

    def getRobot(self):
        """
        获得使用的玩家类，用于设置掉线后放置玩家的拷贝
        """
        return CommonPlayer()

    def doAfterRoomFull(self):
        """
        人满后操作
        """
        pass

    def getPartyRoomRule(self):
        """
        娱乐模式规则
        """
        return []
        """
        胡牌是否即刻结束并结算游戏
        """
        return True

#++++++++++++++++++++ 房间服务可重写接口 end ++++++++++++++++++++
