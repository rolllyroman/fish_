#!/usr/bin/env python
# -*- coding:utf-8 -*-

"""
Author: $Author$
Date: $Date$
Revision: $Revision$

Description:
    普通鱼生成缓存
"""

from common.data.fish_levels import FISH_LEVELS_DATA
from common.data.normal_init_areas import FISh_INIT_AREAS

from common.data.pickfish_consts import *
from common.gameobject import GameObject
import random
import math
import copy

import fish_array

from common.log import log

from common.pb_utils import pbAppendRoute, pbAppendFishesBatch, pbAppendFishesData
from common import fish_data_pb2

FISH_GEN_FILENAME = "fishes"

SPECIAL_AREA_LEVELS = (14,16,17,19,20,21,22,23,29,30,31)

class FishGenerator(GameObject):
    def __init__(self, maxSampleCount = 10000):
        self.maxSampleCount = maxSampleCount
        self.level2fishs = dict([(i, []) for i in xrange(len(FISH_LEVELS_DATA))])

    def getFishData(self, level):

        assert level in self.level2fishs
        return random.choice(self.level2fishs[level])

    def generate(self):


        idx = 0
        canGetArea4specail = FISh_INIT_AREAS[:]
        for level, levelData in enumerate(FISH_LEVELS_DATA):

            for i in xrange(self.maxSampleCount):
                sampleFishs = []
                seqMode, countRange = levelData.getModeNCount()
                appearCount = random.randint(countRange[0], countRange[1])
                #出生区域
                if level == GOLD_TIME_FISH_LEVEL:
                    goldTimeAreas = FISh_INIT_AREAS[-3:]
                    goldTimeAreas.append(FISh_INIT_AREAS[0])
                    area = random.choice(goldTimeAreas)
                elif level in SPECIAL_AREA_LEVELS:
                    if not canGetArea4specail:
                        canGetArea4specail = FISh_INIT_AREAS[:]
                    area = random.choice(canGetArea4specail)
                    canGetArea4specail.remove(area)
                else:
                    area = random.choice(FISh_INIT_AREAS)
                #log(u'start area[%s] areas[%s]'%(area, FISh_INIT_AREAS))
                startP, direct, _ = area.getPointNDirect()
                rad = direct.toRadian()
                #log(u'start point[%s] direct[%s] rad[%s]'%(startP, direct, rad))
                startP = startP + (-direct) * (levelData.width/2.0)

                #生成鱼
                prevFish = None
                initRot = None
                firstSpeed = None
                firstX = None
                firstY = None
                firstDuration = None
                route = []
                #log(u'fish level[%d] appear count[%d]'%(level, appearCount))
                for i in xrange(appearCount):
                    #计算dice点数
                    if appearCount == 1 and random.random() < levelData.dice_odds:
                        dice = random.randint(1, 6)
                    else:
                        dice = 0
                    fish = None
                    #第一只鱼才需要生成route
                    if not prevFish:
                        #随机一个旋转次数
                        rotTimes = levelData.getRotTimes()
                        #初始朝向
                        initRot = math.degrees(rad)
                        #初始速度
                        firstSpeed = levelData.getSpeed()
                        #持续时间
                        firstDuration = duration = levelData.getPerTime()
                        #log(u'first pos[%s,%s] rot[%s] rad[%s] speed[%s] duration[%s]'%(startP.x, startP.y, initRot, rad, firstSpeed, duration))
                        pbAppendRoute(route, 0, firstSpeed, duration)
                        #log(u'dir change count[%s]'%(rotTimes))
                        if seqMode != FISH_SEQMODE_SIDEBYSIDE:
                            lastIdx = rotTimes - 1
                            for j in xrange(rotTimes):
                                rot = levelData.getRot()
                                rotSpeed = levelData.getRotSpeed()
                                if rot < 0:
                                    rotSpeed = -rotSpeed
                                duration = levelData.getPerTime()
                                speed = levelData.getSpeed()
                                #算出旋转的时间
                                rotDuration = float(rot)/rotSpeed
#                                    log(u'rotate angle[%s] rotSpeed[%s] speed[%s] rotDuration[%s] totalDuration[%s]'%
#                                        (rot, rotSpeed, speed, rotDuration, duration))
                                pbAppendRoute(route, rotSpeed, speed, rotDuration)
                                deltaDuration = duration - rotDuration
                                #还剩余时间就是无角速度的移动
                                if deltaDuration > 0:
                                    pbAppendRoute(route, 0, speed, deltaDuration)
                                    #log(u'move extend sec[%s]'%(deltaDuration))
                                elif j == lastIdx:
                                    pbAppendRoute(route, 0, speed, 0)
                                firstDuration += duration
                        #最后一个节点设得更远,移动30秒试试
                        extSec = FISH_EXT_DURATION
                        route[-1].duration += extSec
                        firstDuration += extSec

                        prevFish = fish = fish_array.FishInitData(idx, level, levelData.order, initRot, \
                            startP.x, startP.y, firstDuration, levelData.getMulti() * (dice if dice > 0 else 1), levelData.getPickedRate(), dice, route, 0)
                    else:
                        #复制路径
                        timestampDelta = 0
                        route = copy.deepcopy(prevFish.route)
                        offsetPos = direct.perp()
                        duration = firstDuration
                        if seqMode == FISH_SEQMODE_ONEBYONE:
                            #根据间隔计算速度和时间差
                            #timestampDelta = int(((levelData.width + levelData.seq_offset)*i/float(firstSpeed))*1000)
                            offsetDir = -direct
                            offset = (levelData.width + levelData.seq_offset)*i
                            offsetPos = offsetDir * offset
                            deltaDuration = offset/float(firstSpeed)
                            route[0].duration += deltaDuration
                            duration += deltaDuration
                        elif seqMode == FISH_SEQMODE_SIDEBYSIDE:
                            #根据方向计算间隔
                            offsetDir = direct.rotateSelfByRadian(-math.pi/2.0).normalize()
                            offsetPos = offsetDir * (levelData.height + levelData.seq_offset) * i
                        elif seqMode == FISH_SEQMODE_COLONY:
                            #根据方向计算间隔
                            offsetDir = direct.rotateSelfByRadian(random.uniform(math.pi/2, math.pi+ math.pi/2)).normalize()
                            offsetPos = offsetDir * random.randint(levelData.height, levelData.seq_offset + levelData.height)
#                            straightRoute = []
#                            for rp in route:
#                                if not rp.rotSpeed and rp.speed <= 100:
#                                    straightRoute.append(rp)
#                            for rp in straightRoute:
#                                swingCount = random.randint(1,4)
#                                if not swingCount:
#                                    continue
#                                durationPerSwing = rp.duration / (swingCount*2)
#                                speed = rp.speed
#                                idx = route.index(rp)
#                                route.remove(rp)
#                                for i in xrange(swingCount):
#                                    rotSpeed = random.randint(-10,10)
#                                    route.insert(idx, RouteNode(rotSpeed, speed, durationPerSwing))
#                                    route.insert(idx, RouteNode(-rotSpeed, speed, durationPerSwing))
                        else:
                            offsetPos.x = offsetPos.y = 0
                        fish = fish_array.FishInitData(idx, level, levelData.order, initRot, \
                            startP.x + offsetPos.x, startP.y + offsetPos.y, \
                            duration, levelData.getMulti() * (dice if dice > 0 else 1), levelData.getPickedRate(), dice, route, timestampDelta)

                    idx += 1
                    sampleFishs.append(fish)

                self.level2fishs[level].append(sampleFishs)

    def save(self):
        """
        """
        fishesProto = fish_data_pb2.FishBatches()
        for level, levelData in enumerate(FISH_LEVELS_DATA):
            for fishes in self.level2fishs[level]:
                pbAppendFishesBatch(fishesProto.fishesBatch, fishes)

        f = open(FISH_GEN_FILENAME, 'wb')
        f.write(fishesProto.SerializeToString())
        f.close()

    def saveC(self):
        """
        """
        fishesProto = fish_data_pb2.FishesData()
        for level, levelData in enumerate(FISH_LEVELS_DATA):
            for fishes in self.level2fishs[level]:
                pbAppendFishesData(fishesProto.fishes, fishes)

        f = open(FISH_GEN_FILENAME + '_c', 'wb')
        f.write(fishesProto.SerializeToString())
        f.close()
        
        f = open('fish_data_c/' + FISH_GEN_FILENAME + '_c.bin', 'wb')
        f.write(fishesProto.SerializeToString())
        f.close()

    def load(self):
        """
        """
        fishesProto = fish_data_pb2.FishBatches()
        f = open(FISH_GEN_FILENAME, 'rb')
        fishesProto.ParseFromString(f.read())
        f.close()

        #print fishesProto.fishesBatch[0].fishes[0]
        idx = 0
        for fishesBatch in fishesProto.fishesBatch:
            sampleFishs = []
            for _fish in fishesBatch.fishes:
                levelData = FISH_LEVELS_DATA[_fish.level]
                fish = fish_array.FishInitData(idx, _fish.level, levelData.order, _fish.rot, \
                    _fish.x, _fish.y, _fish.duration, levelData.getMulti() * (_fish.dice if _fish.dice > 0 else 1), levelData.getPickedRate(), _fish.dice, None, _fish.offset)
                idx += 1
                sampleFishs.append(fish)
            self.level2fishs[_fish.level].append(sampleFishs)
        #print self.level2fishs[0][0][0].level, self.level2fishs[0][0][0].initRot, self.level2fishs[0][0][0].x, self.level2fishs[0][0][0].y, 