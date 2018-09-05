# -*- coding:utf-8 -*-
#!/bin/python

"""
Author: $Author$
Date: $Date$
Revision: $Revision$

Description: Player peer
"""

from common.common_player import CommonPlayer
from common.common_db_define import *
from common.protocols.mahjong_consts import *
from common.log import *
from common.data.pickfish_consts import MAX_GOLD_TIME_COUNT
from common.bet_detail_pb2 import betDetail
from common.pb_utils import *
from datetime import datetime

MAX_LOCK_COUNT = 10

class Player(CommonPlayer):
    def __init__(self):
        super(Player, self).__init__()

        self.isTrial = False
        self.isAI = False

        #游戏局内数据
        self.gunType = 0
        self.gunTypeEndTimestamp = 0
        self.gunLevel = 0
        self.gunCoin = 0
        self.gunDirX = 0
        self.gunDirY = 0

        #黄金时刻相关数据，每种房间单独保存
        self.goldTimeCount = 0#MAX_GOLD_TIME_COUNT
        self.goldTimeEndTimestamp = 0

        self.oddsUpDelta = 1

        self.isOutCoin = False
        self.isInCoin = False

        self.tempBetCoin = 0
        self.tempBetCount = 0
        #补偿金币，本次登录有效（每100金币投注补偿1金币，1%的返利）
        self.coverCoin = 0
        self.coverBetCoin = 0
        self.betDetail = []

        #任务
        self.getPrizeCount = 0
        self.getNextPrizeCoin = -1

        #历史投注数据
        self.day2BetData = {}
        self.day2ProfitData = {}
        self.dayAddBetData = {}
        self.dayAddProfitData = {}
        self.allProfit = 0

        #排行榜相关临时数据
        # self.tmpProfitData = {}
        # self.tmpCoinData = {}
        self.tmpAllProfit = None
        self.tmpAllCoin = 0

        #锁鱼次数
        self.lockCount = 0

        # 机率
        self.addChance = 1.3 # 每次增加多少
        self.chanceDefault = 1 # 默认值
        self.chanceInterface = 1 # 应用值
        self.underWater = 0.73
        self.lastBotScore = 0

    def upChance(self):
        "提升机率"
        print(u"提升机率:%s" % self.addChance)
        self.chanceInterface = self.addChance

    def clearChance(self):
        "清除机率"
        print(u"降低机率:%s" % self.underWater)
        self.chanceInterface = self.chanceDefault * self.underWater

    def resetGoldTime(self):
        self.goldTimeEndTimestamp = 0

    def isInGoldTime(self):
        return self.goldTimeEndTimestamp > 0

    def loadDB(self, playerTable, isInit=True, account = None):
        super(Player, self).loadDB(playerTable, isInit, account)

        redis = self.factory.getPublicRedis()
        curDateStr = self.factory.getDate()
        if isInit:
            #日投注收益
            try:
                self.day2BetData[curDateStr] = int(redis.hincrbyfloat(PLAYER_FISH_BET_DATA4DAY%(self.uid, curDateStr), 'bet', 0))
            except:
                self.day2BetData[curDateStr] = 0
            try:
                self.day2ProfitData[curDateStr] = int(redis.hincrbyfloat(PLAYER_FISH_BET_DATA4DAY%(self.uid, curDateStr), 'profit', 0))
            except:
                self.day2ProfitData[curDateStr] = 0
            self.allProfit = int(redis.hincrbyfloat(PLAYER_FISH_BET_DATA4ALL%self.uid, 'profit',0))

            #黄金时刻
            self.goldTimeCount = redis.get(FORMAT_USER_GAME_DATA_GOLD_TIME_COUNT%(self.account, self.factory.ID))
            if not self.goldTimeCount:
                self.goldTimeCount = 0
            else:
                self.goldTimeCount = int(self.goldTimeCount)
                self.goldTimeCount = 0

            gunCoin = redis.get(FORMAT_USER_GAME_DATA_GUN_COIN%(self.account, self.factory.ID))
            gunInfo = self.factory.globalCtrl.gunLevels[0]
            if gunCoin and float(gunCoin):
                gunCoin = float(gunCoin)
                if gunCoin >= gunInfo.coinRange[0] and gunCoin <= gunInfo.coinRange[1] and\
                        (not (gunCoin-gunInfo.coinRange[0])%gunInfo.stepCoin):
                    self.gunCoin = gunCoin
            else:
                self.gunCoin = gunInfo.coinRange[0]

        #锁鱼次数
        # lockCount = redis.get(PLAYER_DAY_LOCK_COUNT%(self.account, curDateStr))
        lockCount = redis.hget(playerTable, 'lockCount')
        try:
            self.lockCount = int(lockCount)
        except:
            self.lockCount = 0
            # self.lockCount = MAX_LOCK_COUNT
            # redis.set(PLAYER_DAY_LOCK_COUNT%(self.account, curDateStr), MAX_LOCK_COUNT)
        if self.lockCount < 0:
            self.lockCount = 0

    def bet(self, betCoin, addCoin, pickFishs, tax):
        """
        投注
        """
        if betCoin:
            self.betCoin += betCoin
            self.totalBetCoin += betCoin

            #日投注数据
            curDateStr = self.factory.getDate()
            if curDateStr not in self.day2BetData:
                self.day2BetData[curDateStr] = 0
            if curDateStr not in self.dayAddBetData:
                self.dayAddBetData[curDateStr] = 0
            self.day2BetData[curDateStr] += betCoin
            self.dayAddBetData[curDateStr] += betCoin
            # self.tmpCoinData[curDateStr] = self.coin
            self.tmpAllCoin = self.coin

            self.coinRunning += betCoin
            self.tempBetCoin += betCoin
            self.tempBetCount += 1
            coverCoinPerUnit = self.game.server.globalCtrl.coverCoinPerUnit
            # if coverCoinPerUnit and not self.isOutCoin and addCoin <= 0:
                # self.coverBetCoin += betCoin
                # coverCoinUnit = self.game.server.globalCtrl.coverCoinUnit
                # if self.coverBetCoin > coverCoinUnit:
                    # self.coverCoin += coverCoinPerUnit*(self.coverBetCoin/coverCoinUnit)
                    # self.coverBetCoin = self.coverBetCoin%coverCoinUnit
        profitCoin = addCoin - betCoin
        realCoin = 0
        taxCoin = 0
        if profitCoin:
            realCoin, taxCoin = self.profit(profitCoin, tax)
        if self.isTrial:
            return realCoin
        if not self.isAI:
            betData = {}
            betData['timestamp'] = int(time.time()*1000)
            betData['bet'] = formatCoin(betCoin)
            betData['profit'] = formatCoin(realCoin)
            betData['fishes'] =[]
            betData['fishes'].extend(pickFishs)
            self.betDetail.append(betData)
        return realCoin

    def profit(self, coin, tax):
        taxCoin = 0
        if coin > 0:
            taxCoin = coin * tax
            coin -= taxCoin
        else:
            taxCoin = 0
        self.taxCoin += taxCoin
        self.coin += coin
        self.profitCoin += coin
        self.totalProfitCoin += coin
        self.totalProfitCoin4Ticket += coin
        self.coinDelta += coin
        self.allProfit += coin
        self.tmpAllProfit = self.allProfit

         #日收益数据
        curDateStr = self.factory.getDate()
        if curDateStr not in self.dayAddProfitData:
            self.dayAddProfitData[curDateStr] = 0
        if curDateStr not in self.day2ProfitData:
            self.day2ProfitData[curDateStr] = 0
        self.dayAddProfitData[curDateStr] += coin
        self.day2ProfitData[curDateStr] += coin
        # self.tmpProfitData[curDateStr] = self.day2ProfitData[curDateStr]

        return coin, taxCoin

