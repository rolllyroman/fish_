# -*- coding:utf-8 -*-
#!/bin/python

"""
Author: $Author$
Date: $Date$
Revision: $Revision$

Description:
鱼管理类
"""

from twisted.internet import reactor

from common.data.fish_levels import FISH_LEVELS_DATA, FISH_ORDER2LEVELS, FISH_LEVELS_LIMIT_DATA

from common.pickfish_pb2 import S_C_GenerateFish, S_C_FishArray
from common.pb_utils import pbAppendFishList

from common.gameobject import GameObject
from common.data.pickfish_consts import *
from fish import Fish
import random
import math
import time
from datetime import datetime
from common.log import log

import fish_array
import json

FISH_GEN_AHEAD_MS = 10000
FISH_GEN_BATCH_MS = 48000
FISH_REMOVE_AFTER_ARRAY = 8000#15000

NEED_LIMIT_LEVELS = (19, 30, 31)

class FishMgr(GameObject):
    def __init__(self, game, maxCountOfFishs = 100):
        self.game = game
        self.maxCountOfFishs = maxCountOfFishs
        globalCtrl = self.game.server.globalCtrl
        if not globalCtrl.addFishMinCount:
            globalCtrl.addFishMinCount = maxCountOfFishs
        if not globalCtrl.addFishMaxCount:
            globalCtrl.addFishMaxCount = maxCountOfFishs
        self.idx = 0
        self.fishs = []
        self.fishIdx = {}
        self.level2Fishs = dict([(i, []) for i in xrange(len(FISH_LEVELS_DATA))])
        self.beFreezeFishes = []

        self.removeFishTimestamp = 0
        self.removeFishes = []

        self.reloadLevel2appearCount()

        #log('Fish level and counts: %s'%(self.level2appearCount))

        self.fishArray = fish_array.FishArray(self)
        self.nextFishGenTimestamp = 0
        self.lastFishArrayTimestamp = self.game.getTimestamp()
        self.fishArrayAppearTick = random.randint(FISH_ARRAY_APPEAR_SEC[0], FISH_ARRAY_APPEAR_SEC[1]) * 1000

        #鱼的时间限制
        self.level2lastAddTime = {}
        self.index2deathTimes = {}

        #出界鱼再游回相关
        # self.rmLevel2Fish = {}
        self.rmLevel2Count = {}

    def reloadLevel2appearCount(self):
        totalRate = 0
        globalCtrl = self.game.server.globalCtrl

        for level, levelData in enumerate(FISH_LEVELS_DATA):
            if globalCtrl.level2limitCount and level not in globalCtrl.level2limitCount:
                totalRate += levelData.rate_appear
            elif not levelData.limit_count:
                totalRate += levelData.rate_appear

        maxCountOfFishs = random.randint(globalCtrl.addFishMinCount, globalCtrl.addFishMaxCount)
        #print(u"渔场当前刷新多少条鱼:%s" % maxCountOfFishs)

        if maxCountOfFishs <= 0:
            maxCountOfFishs = self.maxCountOfFishs
        for limitCount in globalCtrl.level2limitCount.itervalues():
            maxCountOfFishs -= limitCount
        maxCountOfFishs = max(0, maxCountOfFishs)

        self.level2appearCount = dict([(level, (int(math.ceil(levelData.rate_appear/totalRate * maxCountOfFishs)) if not levelData.limit_count else levelData.limit_count)) \
            for level, levelData in enumerate(FISH_LEVELS_DATA)])
        # print(u"检查：%s, sum:%s" % (json.dumps(self.level2appearCount, indent=1), sum(self.level2appearCount.values())))

        for level, limitCount in globalCtrl.level2limitCount.iteritems():
            if level in self.level2appearCount:
                self.level2appearCount[level] = limitCount

    def destroy(self):
        self.fishs = []
        self.fishIdx.clear()
        self.level2Fishs.clear()

        self.level2Fishs = dict([(i, []) for i in xrange(len(FISH_LEVELS_DATA))])

    def onBomb(self, timestamp):
        for fish in self.fishs[:]:
            if fish.isIn(timestamp):
                self.remove(fish)

    def refresh(self, timestamp):
        """
        刷新鱼
        """
        #self.checkFishOut(timestamp)
        #暂清鱼(鱼阵出现)
        self.reloadLevel2appearCount()

        if self.removeFishes:
            if timestamp >= self.removeFishTimestamp:
                for _fish in self.removeFishes:
                    if _fish.id in self.fishIdx:
                        self.remove(_fish)
                self.removeFishes = []
                self.removeFishTimestamp = 0

        #鱼阵激活
        if not self.fishArray.isStarted:
            if timestamp - self.lastFishArrayTimestamp >= self.fishArrayAppearTick:
                self.game.randomBgIdx()

                #清鱼缓存
                self.removeFishes = []
                self.removeFishes.extend(self.fishs)
                self.removeFishTimestamp = timestamp + FISH_REMOVE_AFTER_ARRAY

                fishArrayProto = S_C_FishArray()
                fishArrayProto.timestamp = timestamp
                fishArrayProto.bgIdx = self.game.bgIdx
                fishArrayData = self.game.server.fishArrayGenerator.getFishData()
                log(u'Fish Array gen fishs count[%d] duration[%s] fish idx[%d]'% \
                    (len(fishArrayData.fishDatas), fishArrayData.duration, self.idx))
                for fishData in fishArrayData.fishDatas:
#                    log(u'fish level[%d] initRot[%d] initPos[%s, %s] duration[%s] multi[%d] rate[%d] route[%s]'% \
#                        (fishData.level, fishData.initRot, fishData.x, fishData.y, fishData.duration, fishData.multi, fishData.rate, fishData.route))
                    fish = Fish(self.genId(), fishData.idx, fishData.level, fishData.order, timestamp + fishData.timestampOffset, fishData.initRot, \
                        fishData.x, fishData.y, fishData.duration, fishData.multi, fishData.rate, fishData.dice, fishData.route)
                    self.add(fish)
                    pbAppendFishList(fishArrayProto.fishs, fish, self.game.server.showFishHitCoiunt)
                self.game.sendAll(fishArrayProto)
                self.fishArray.duration = fishArrayData.duration
                self.fishArray.start(timestamp)
            else:
                self.genFishs(timestamp)
                #log(u'current fishs count[%s]'%(len(self.fishs)))
        else:
            #没鱼了或鱼阵结束
            if self.fishArray.isOver(timestamp):
                log(u'fish array over duration[%s]'%(self.fishArray.duration))
                self.destroy()
                self.fishArray.stop()
                self.nextFishGenTimestamp = 0
                self.lastFishArrayTimestamp = timestamp
                self.fishArrayAppearTick = random.randint(FISH_ARRAY_APPEAR_SEC[0], FISH_ARRAY_APPEAR_SEC[1]) * 1000
                self.genFishs(timestamp)

    def isEmpty(self):
        return not self.fishs

    def genId(self):
        self.idx += 1
        return self.idx

    def getFish(self, id):
        if id not in self.fishIdx:
            return False
        return self.fishIdx[id]

    def getValidFishes(self):
        if self.removeFishes:
            return [fish for fish in self.fishs if fish not in self.removeFishes]
        return self.fishs

    def getNotInFishes(self, timestamp):
        return [fish for fish in self.fishs if ((not fish.isIn(timestamp)) and (not fish.isOut(timestamp)))]

    def add(self, fish):
        assert fish
        self.fishs.append(fish)
        self.fishIdx[fish.id] = fish
        self.level2Fishs[fish.level].append(fish)

    def remove(self, fish):
        assert fish
        self.level2Fishs[fish.level].remove(fish)
        del self.fishIdx[fish.id]
        self.fishs.remove(fish)

    def pickRemove(self, fish): #打中鱼
        if self.fishArray.isStarted:
            return
        for index, fishLevelsLimit in enumerate(FISH_LEVELS_LIMIT_DATA):
            fishLevels = fishLevelsLimit.fishLevels
            if fishLevelsLimit.death_min_limit_time and fish.level in fishLevels:
                if index not in self.index2deathTimes:
                    self.index2deathTimes[index] = []
                self.index2deathTimes[index].append(self.game.getTimestamp())

    def outRemove(self, fish): #游出界
        if self.fishArray.isStarted:
            return

        # if fish.level not in self.rmLevel2Fish:
            # self.rmLevel2Fish[fish.level] = []
        # self.rmLevel2Fish[fish.level].append(fish)
        # if fish.level not in self.rmLevel2Count:
            # self.rmLevel2Count[fish.level] = 0
        # self.rmLevel2Count[fish.level] += 1

    def genFishs(self, timestamp):
        if self.nextFishGenTimestamp and timestamp < self.nextFishGenTimestamp:
            return

        #log(u'Before gen timestamp[%s] nextTime[%s]'%(timestamp, self.nextFishGenTimestamp))
        genFishTimestamp = timestamp if not self.nextFishGenTimestamp else self.nextFishGenTimestamp + FISH_GEN_AHEAD_MS

        self.nextFishGenTimestamp = genFishTimestamp + FISH_GEN_BATCH_MS - FISH_GEN_AHEAD_MS

        reactor.callInThread(self.genFishsT, genFishTimestamp)

    def genFishsT(self, genFishTimestamp):
        newFishs = []
        nowTime = int(time.time()) * 1000
        cooldownTimes = []
        startDate = datetime(2018, 2, 16).date()
        testDate = datetime(2018, 2, 9).date()
        endDate = datetime(2018, 2, 20).date()
        curDate = datetime.now().date()
        for level, levelData in enumerate(FISH_LEVELS_DATA):
            if level == 34:
                if curDate != testDate:
                    if curDate < startDate or curDate > endDate:
                        continue

            #鱼按出现几率分配出生个数
            count = self.level2appearCount[level]
            # if level in self.rmLevel2Count: #移除的鱼加回来
                # count = max(self.rmLevel2Count[level], count)
                # if count > levelData.limit_count:
                    # count = levelData.limit_count
                # self.rmLevel2Count[level] -= count
                # self.rmLevel2Count[level] = max(self.rmLevel2Count[level], 0)
            fishDatas = []
            curCount = 0
            # if levelData.limit_count and (level in NEED_LIMIT_LEVELS) and (len(self.level2Fishs[level]) >= levelData.limit_count):
                # continue
            if not count:
                continue
            while True:
                # print(u"现在等级:%s" % level)
                tmpFishs = self.game.server.fishGenerator.getFishData(level)
                curCount += len(tmpFishs)
                if curCount > count:
                    fishDatas.append(tmpFishs[:curCount-count])
                    break
                else:
                    fishDatas.append(tmpFishs)
                    if curCount == count:
                        break
            newFishs.extend(fishDatas)

        random.shuffle(newFishs)

        totalCount = len(newFishs)
        sliceMs = FISH_GEN_BATCH_MS/totalCount
        genFishProto = S_C_GenerateFish()
        idx = 0
        #firstFish = None
        tempFish = []
        level2Count = {}
        index2limitCount = {}
        for fishs in newFishs:
            for fishData in fishs:
                level = fishData.level
                fishTime = genFishTimestamp + sliceMs*idx + fishData.timestampOffset
                fishLevelData = FISH_LEVELS_DATA[level]

                #多鱼限制
                isBeLimit = False
                for index, fishLevelsLimit in enumerate(FISH_LEVELS_LIMIT_DATA):
                    fishLevels = fishLevelsLimit.fishLevels
                    min_limit_time = fishLevelsLimit.death_min_limit_time * 1000
                    if index in self.index2deathTimes: #死亡的鱼数
                        for deathTime in self.index2deathTimes[index][:]:
                            if (fishTime - deathTime) >= min_limit_time:
                                 self.index2deathTimes[index].remove(deathTime)
                        waitFishCount = len(self.index2deathTimes[index])
                    else:
                        waitFishCount = 0
                    if level in fishLevels:
                        if index not in index2limitCount:
                            index2limitCount[index] = 0
                        if fishLevelsLimit.limit_count and index2limitCount[index] >= fishLevelsLimit.limit_count - waitFishCount:
                            isBeLimit = True
                            break
                        if not index2limitCount[index]:
                            lastAddTime = self.getLastAddTime4fishs(fishLevels)
                            min_limit_time = fishLevelsLimit.min_limit_time * 1000
                            max_limit_time = fishLevelsLimit.max_limit_time * 1000
                            if (fishTime - lastAddTime) < min_limit_time: #等待时间不足
                                # fishTime = min(genFishTimestamp + fishData.timestampOffset + FISH_GEN_BATCH_MS,\
                                        # lastAddTime + min_limit_time)
                                # if (fishTime - lastAddTime) < min_limit_time:
                                isBeLimit = True
                                break
                            # if max_limit_time and (fishTime - lastAddTime) > max_limit_time: #等待时间超出
                                # fishTime = max(genFishTimestamp, fishTime - max_limit_time * 1000)
                        index2limitCount[index] += 1
                if isBeLimit:
                    break

                max_together_count = fishLevelData.max_together_count
                isTogether = False
                if level not in self.level2lastAddTime:
                    self.level2lastAddTime[level] = 0
                if max_together_count: #可同时刷出多只
                    if level not in level2Count:
                        level2Count[level] = 0
                    elif level2Count[level] + 1 < (random.random() * max_together_count):
                        fishTime = self.level2lastAddTime[level] + 100
                        isTogether = True
                    level2Count[level] += 1
                if not isTogether: #时间限制
                    lastAddTime = self.level2lastAddTime[level]
                    min_limit_time = fishLevelData.min_limit_time * 1000
                    max_limit_time = fishLevelData.max_limit_time * 1000
                    if (fishTime - lastAddTime) < min_limit_time: #等待时间不足
                        # fishTime = min(genFishTimestamp + fishData.timestampOffset + FISH_GEN_BATCH_MS, lastAddTime + min_limit_time)
                        # if (fishTime - lastAddTime) < min_limit_time:
                        if level in level2Count:
                            level2Count[level] -= 1
                        break
                    # if max_limit_time and (fishTime - lastAddTime) > max_limit_time: #等待时间超出
                        # fishTime = max(genFishTimestamp, fishTime - max_limit_time * 1000)
                self.level2lastAddTime[level] = fishTime #记录每种鱼的最后添加时间
                fish = Fish(self.genId(), fishData.idx, fishData.level, fishData.order, fishTime, fishData.initRot, \
                    fishData.x, fishData.y, fishData.duration, fishData.multi, fishData.rate, fishData.dice, fishData.route)
                #if not firstFish:
                #    firstFish = fish
                if fish.dice:
                    log(u'gen fish id[%s] idx[%s] dice[%s] level[%s]'%(fish.id, fish.idx, fish.dice, fish.level))
                self.add(fish)
                tempFish.append(fish)
                pbAppendFishList(genFishProto.fishs, fish, self.game.server.showFishHitCoiunt)
            idx += 1
        # print(u"生成了鱼的数量：%s" % len(tempFish))
        self.game.sendAll(genFishProto)
        #log(u'First fish timestamp[%s] level[%s]'%(firstFish.timestamp, firstFish.level))
        #log(u'Last fish timestamp[%s] level[%s]'%(fish.timestamp, fish.level))

        #log(u'Gen fishs[%s] timestamp[%s] nextTime[%s]'%(totalCount, genFishTimestamp, self.nextFishGenTimestamp))

    def getLastAddTime4fishs(self, levels): #多条鱼的最后生成时间
        maxLastAddTime = 0
        for level in levels:
            if level not in self.level2lastAddTime:
                continue
            lastAddTime = self.level2lastAddTime[level]
            if lastAddTime > maxLastAddTime:
                maxLastAddTime = lastAddTime
        return maxLastAddTime

    def checkFishOut(self, timestamp):
        """
        每次遍历一定数量的鱼，把出界的鱼删除
        """
        deadFishs = []
        for fish in self.fishs[:]:
            if fish.isOut(timestamp):
                self.remove(fish)

    def freezing(self, timestamp):
        """
        全屏冻结处理
        """
        ms = FREEZING_SECS * 1000
        self.nextFishGenTimestamp += ms
        self.fishArrayAppearTick += ms
        for fish in self.fishs:
            if not fish.isIn(timestamp):
                fish.timestamp += ms
                fish.outTimestamp += ms + 2000
            else:
                self.beFreezeFishes.append(fish.id)
            if not fish.isOut(timestamp):
                fish.outTimestamp += ms + 2000
