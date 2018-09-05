#!/usr/bin/env python
# -*- coding:utf-8 -*-

"""
Author: $Author$
Date: $Date$
Revision: $Revision$

Description:
    游戏配置
"""

from common.log import log
from common.gameobject import GameObject
from common import consts
from common.common_db_define import *
from common.protocols.mahjong_consts import *
from common.protocols import *
from common.data.fish_levels import FISH_LEVELS_DATA
from common.data.gunInfo import GunInfo

import redis_instance

from datetime import datetime

import random
import math
MAX_LOSE_COIN = 100000.0
ODDS_OUT = 10000.0
#MAX_TAN_DELTA = 1.41
#MAX_TAN = math.tan(MAX_TAN_DELTA)
ODDS_NAGATIVE_OFFSET = 0.01
ODDS_MIN = 0.2
#单个玩家最高赢输比2%
MAX_PLAYER_PROFIT_RATE = 0.02
ODDS_NORMAL = 0.95
ODDS_LIMIT = 0.5

TICK_GAMES_COUNT = 10

# GAME_NUM = 1000

ODDS_LIMIT_DELTA = ODDS_LIMIT - ODDS_MIN
AI_ODDS = 0.95
#默认抽水率为5%
DEFAULT_ODDS_PUMPING = 0.00

MAX_DESK = 20   #原默认值为10

#incomeRate=入分率（杀分比例）
#taxRate=抽分率（明面抽成比例）
#betCoin=总投注额
#总抽水额度=betCoin*(incomeRate+taxRate) - betCoin*incomeRate*taxRate

RESERVED_RATE = 0.001
POOLCOIN_RATE = 0.001
SHARE_RATE_RANGE = (0.4, 0.5)
MAX_POOL_COIN_PER_TIME = 1000
ODDS_IN = 1.0/10

PAYOUT_SEC_RANGE = (12, 30)

#补偿金币单位，本次登录有效（每$COVER_COIN_UNIT金币投注补偿$COVER_COIN_PER_UNIT金币）
COVER_COIN_UNIT = 18
COVER_COIN_PER_UNIT = 0

POOL_PAYOUT_COINS = 1000#(1000, 10000, 30000)
DEFAULT_PICK_TICKET_RATE = 1 #打中奖票默认概率
DEFAULT_PICK_TICKET_GET_RATE = 0.15
MAX_ROOM_NUM = 1000

class GlobalControl(GameObject):
    def __init__(self, server):
        self.loadRoomInfo()
        self.num2game = {}
        self.useRoomNum = 0

        self.currencyAgentCashRefreshLock = False

        self.outCoinAccountsPool = {}
        self.inCoinAccountsPool = {}

        self.reservedInCoin = 0
        self.reservedCoin = 0
        self.payoutCoins = 0
        self.poolCoins = 0
        self.payoutTimestamps = 0
        self.payoutAddRate = 1

        #任务
        self.maxGetPrizeCount = -1
        self.getNextPrizeAddCoin = -1
        self.getPrizeCoinList = []

        #奖票
        # self.bet2TicketRate = []
        self.pickTicketRate = DEFAULT_PICK_TICKET_RATE #打中奖票概率
        self.pickTicketNeedCoin = 0 #需要流水
        self.ticketCoin = 0 #奖票价值
        self.pickTicketGetRate = DEFAULT_PICK_TICKET_GET_RATE #每次获得奖票中的百分比
        self.maxGetTicketCount = 0
        self.getTicketWaitTime = []

        #鱼场设置
        self.level2needCount = {}#打中鱼需要的最低次数
        self.level2limitCount = {}#鱼个数限制
        self.addFishMaxCount = 0 #最大刷新个数
        self.addFishMinCount = 0 #最小刷新个数



        server.loadChannalData(self)
        self.reloadOdds()
        self.loadFishInfo()
        self.loadGunInfo()

        self.reloadCoverCoin(COVER_COIN_UNIT, COVER_COIN_PER_UNIT)

    def loadRoomInfo(self):

        self.tickGameIdx = 0
        self.gameList = []

    def getEmptyGames(self):
        return [game for game in self.gameList if (game.getEmptyChair() != consts.SIDE_UNKNOWN)]

    def getTickGames(self):
        countGames = len(self.gameList)
        #log('games count[%d] tickIdx[%d]'%(countGames, self.tickGameIdx))
        if countGames <= 0:
            return []
        if self.tickGameIdx >= countGames:
            self.tickGameIdx = 0
        ret = self.gameList[self.tickGameIdx:self.tickGameIdx+TICK_GAMES_COUNT]
        self.tickGameIdx += TICK_GAMES_COUNT
        return ret

    def getRoomNum(self):
        if self.useRoomNum >= MAX_ROOM_NUM:
            if len(self.gameList) < MAX_ROOM_NUM/2:
                self.useRoomNum = 0
        while True:
            self.useRoomNum += 1
            if self.useRoomNum not in self.num2game:
                break
        return self.useRoomNum

    def addGame(self, game, gameId):
        redis = redis_instance.getInst(PUBLIC_DB)
        gameTable = GAME_TABLE%(gameId)
        gameName = redis.hget(gameTable,'name')
        if gameName:
            game.roomName = gameName
        game.roomId = self.getRoomNum()
        game.gameName = gameName
        self.num2game[game.roomId] = game
        self.gameList.append(game)
        return True

    def removeGame(self, game):
        if game.roomId in self.num2game:
            del self.num2game[game.roomId]
        if game in self.gameList:
            self.gameList.remove(game)

    def loadFishInfo(self):
        # self.fishesCapacity = [40 for data in FISH_LEVELS_DATA]
        # self.fishesCapacity[0] = 120
        # self.fishesCapacity[1] = 72
        # self.fishesCapacity[2] = 48
        # self.fishesCapacity[3] = 48
        # self.fishesCapacity[7] = 40
        # self.fishesCapacity[10] = 48

        self.fishesCapacity = []
        for fishData in FISH_LEVELS_DATA:
            if fishData.limit_count:
                self.fishesCapacity.append(fishData.limit_count * 2)
            elif fishData.rate_appear:
                self.fishesCapacity.append(40)
            else:
                self.fishesCapacity.append(1)

    def reduceJackpot(self, redis, game, money):
        " 减少奖池的金币 "
        redis.hincrby(FISH_JACKPOT, game.roomId, -money)

    def getJoackpot(self, redis, game):
        " 获取奖池内的金币 "
        _jockpot = redis.hget(FISH_JACKPOT, game.roomId)
        return _jockpot

    def loadGunInfo(self):
        self.bulletSpeeds = [
            #level0
            850,
            #level1
            1000,
            #level2
            1150
        ]
        self.gunLevels = [#level1
            GunInfo(
                    level = 0,
                    coinRange = (float(self.base_coin),float(self.max_base_coin)),
                    stepCoin = float(self.step_base_coin)
            )
        ]

    def getGunInfo(self, level):
        _len = len(self.gunLevels)
        assert level >=0 and level < _len, "gunLevels[%d] not in range(0,%d)"%(level, 0, _len)
        return self.gunLevels[level]

    def bet(self, player, betCoin):
        """
        投注刷新奖池
        """
        if not betCoin:
            return

        if player.isInCoin:
            self.reservedInCoin += betCoin * self.rtpIn
            return

        # self.reservedCoin += betCoin * RESERVED_RATE
        returnCoin = betCoin * self.rtp
        poolCoin = 0
        allPayCoin = 0
        poolAddCoins = 0
        if self.oddsOfPumping >= 0:
            if player.isOutCoin:
                poolCoin = betCoin * SHARE_RATE_RANGE[1]
            else:
                poolCoin = betCoin * random.uniform(*SHARE_RATE_RANGE)
                if not player.isAI:
                    poolAddCoins = betCoin * POOLCOIN_RATE
                    self.payoutCoins += poolCoin
                    self.poolCoins += poolAddCoins
                    allPayCoin = poolAddCoins + poolCoin

        player.coverCoin += returnCoin - allPayCoin
        log(u'[player pool info][%s]bet coin[%s] coverCoin[%s]add[%s] payoutCoins[%s]add[%s] poolCoins[%s]add[%s].'\
                %(player.account, betCoin, player.coverCoin, returnCoin - allPayCoin, self.payoutCoins, poolCoin, self.poolCoins, poolAddCoins))
        

    def profit(self, player, addCoin):
        """
        派彩刷新奖池
        """
        if player.isInCoin:
            self.reservedInCoin -= addCoin
            return

        player.coverCoin -= addCoin
        log(u'[player pool info][%s]add coin[%s] coverCoin[%s].'%(player.account, addCoin, player.coverCoin))

    def canGainCoin(self, player, addCoin, curCoin):
        """
        是否可以出特定分
        返回：捕获鱼概率[0,1]
        """
        if player.isInCoin:
            if not curCoin:
                return 0
            if self.reservedInCoin > addCoin:
                return ODDS_IN
            return 0

        if player.coverCoin >= addCoin:
            return ODDS_NORMAL
        return 0

    def reloadOdds(self):
        # self.oddsOfPumping = DEFAULT_ODDS_PUMPING
        # self.taxRate = 0

        self.rate = 1.0 - self.oddsOfPumping
        self.maxPickedRate = 1.0 / self.rate
        # self.resetPoolCoin()

        self.rtp = 1 - self.oddsOfPumping# - RESERVED_RATE*2
        self.rtpIn = 1 - self.oddsOfPumping

    def reloadCoverCoin(self, unit, coinPerUnit):
        """
        每个单位非盈利投注返多少金币
        """
        self.coverCoinUnit = unit
        self.coverCoinPerUnit = coinPerUnit

    def upGunLevelNCoin(self, level, coin):
        """
        升级处理
        """
        _len = len(self.gunLevels)
        assert level >= 0 and level < _len, "gunLevels[%d] not in range(0,%d)"%(level, 0, _len)
        gunInfo = self.gunLevels[level]
        assert coin >= gunInfo.coinRange[0] and coin <= gunInfo.coinRange[1]
        #金币超出上限升级，否则只是加金币
        if coin + gunInfo.stepCoin > gunInfo.coinRange[1]:
            #最大等级循环回去
            if level >= _len - 1:
                level = 0
            else:
                level += 1
            coin = self.gunLevels[level].coinRange[0]
            return level, round(coin, 2)
        else:
            coin += gunInfo.stepCoin
            return level, round(coin, 2)

    def deGunLevelNCoin(self, level, coin):
        """
        降级处理
        """
        _len = len(self.gunLevels)
        assert level >= 0 and level < _len, "gunLevel[%d] not in range(0,%d)"%(level, 0, _len)
        gunInfo = self.gunLevels[level]
        assert coin >= gunInfo.coinRange[0] and coin <= gunInfo.coinRange[1]
        #金币超出下限降级，否则只是减金币
        if coin - gunInfo.stepCoin < gunInfo.coinRange[0]:
            #最小等级循环回去
            if level <= 0:
                level = _len - 1
            else:
                level -= 1
            coin = self.gunLevels[level].coinRange[1]
            return level, coin
        else:
            coin -= gunInfo.stepCoin
            return level, coin

    def tryPayout(self, timestamp, account2players):
        """
        送分激活，释放彩池
        """
        payCoins = self.payoutCoins
        # payoutTimestamps = self.payoutTimestamps
        poolCoins = self.poolCoins
        log(u'[pool info]payCoins[%s] poolCoins[%s].'%(payCoins, poolCoins))
        # for idx in xrange(len(payCoins)):
        if timestamp >= self.payoutTimestamps:
            if payCoins <= 0:
                self.payoutTimestamps = timestamp + random.randint(*PAYOUT_SEC_RANGE) * 1000
                # continue
                return
            #在游戏中的玩家才会成为幸运玩家，根据当天投注额随机一个值
            curPlayers = []
            rand = random.random()
            allTempBetCoin = 0
            for player in account2players.itervalues():
                if player.game:# and player.game.idx == idx:
                    if not player.isInCoin and not player.isOutCoin:
                        if rand < 0.1:
                            if player.tempBetCoin >= 1:
                                # score = random.randint(1, player.tempBetCoin) * random.randint(1, player.tempBetCount)
                                score = player.tempBetCoin
                                allTempBetCoin += player.tempBetCoin
                                curPlayers.append((player, score))
                        elif rand < 0.15:
                            if player.tempBetCount > 50:
                                # score = random.random()
                                score = player.tempBetCoin
                                allTempBetCoin += player.tempBetCoin
                                curPlayers.append((player, score))
                        else:
                            score = -(player.profitCoin + player.coverCoin)
                            if score > 0:
                                score = player.tempBetCoin
                                allTempBetCoin += player.tempBetCoin
                                curPlayers.append((player, score))
                    player.tempBetCoin = player.tempBetCount = 0
            if curPlayers:
                if poolCoins > POOL_PAYOUT_COINS:
                    payCoins += poolCoins
                    log(u'[pay out add]coin[%s].'%(poolCoins))
                    self.poolCoins = 0
                else:
                    payCoins *= self.payoutAddRate
                curPlayers.sort(cmp=GlobalControl.__compareBet, reverse=True)
                # curPlayers = curPlayers[:max(1, len(curPlayers)/8)]
                random.shuffle(curPlayers)
                log(u'[pay out prev]payout coin[%s].'%(payCoins))
                # payout = payCoins/len(curPlayers)
                # averTempBetCoin = allTempBetCoin/len(curPlayers)
                allPayOut = 0
                for player, score in curPlayers:
                    if not allTempBetCoin:
                        break
                    if (player, score) == curPlayers[-1]: #最后一个人固定拿完
                        payout = payCoins
                    else:
                        maxPayoutRate = min(1, score/allTempBetCoin*5)
                        minPayoutRate = max(0, score/allTempBetCoin/2)
                        payout = int(payCoins * random.uniform(*(minPayoutRate, maxPayoutRate)))
                    player.coverCoin += payout
                    payCoins -= payout
                    allPayOut += payout
                    log(u'[pay out succeed]luckyPlayer[%s] payout[%s] score[%s].'%(player.account, payout, score))
                self.payoutCoins -= allPayOut
            self.payoutTimestamps = timestamp + random.randint(*PAYOUT_SEC_RANGE) * 1000

    @staticmethod
    def __compareBet(l, r):
        if l[1] > r[1]:
            return 1
        elif l[1] == r[1]:
            return 0
        else:
            return -1

