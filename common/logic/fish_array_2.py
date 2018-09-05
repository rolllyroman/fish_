#!/usr/bin/env python
# -*- coding:utf-8 -*-

"""
Author: $Author$
Date: $Date$
Revision: $Revision$

Description:
    鱼阵2，等三环鱼阵
"""
from common.data.scene import WIDTH, HEIGHT, CENTER_X, CENTER_Y
from common.data.fish_init_areas import FishInitArea
from common.arith.point_math import Point
from common.data.fish_levels import FISH_LEVELS_DATA
from common.data.pickfish_consts import TOLERATE_LAG_SECS
import fish_array
from common.gameobject import GameObject

import random
import math

from common.pb_utils import pbAppendRoute

class FishArrayInit(GameObject):
    def __init__(self, fishLevels, speed, radius, count, offsetAngle = 0):
        self.fishLevels = fishLevels
        self.speed = speed
        self.radius = radius
        self.count = count
        self.offsetAngle = offsetAngle

class FishArray(fish_array.FishArray):
    def __init__(self, fishMgr):
        super(FishArray, self).__init__(fishMgr)
        #基础速度
        self.speed = 65
        #每个环的半径
        self.radius = 400
        #内环4鱼半径
        self.radiusInner = 160
        self.initArea = FishInitArea(Point(0, CENTER_Y), Point(0, CENTER_Y), Point(WIDTH, CENTER_Y), Point(WIDTH, CENTER_Y))
        self.initDatas = [
            #第一环
            FishArrayInit([1], self.speed, self.radius-100, 36), \
            #第二环
            FishArrayInit([10], self.speed, self.radius-90, 18), \
            #第三环
            FishArrayInit([1], self.speed, self.radius-100, 36), \
            #内环
            FishArrayInit([9, 11, 14], self.speed, self.radiusInner, 4, 45), \
        ]
        #外环大鱼与内环大鱼的平行距离
        self.offsetInOut = 460

    def genFishs(self):
        self.genFishDatas = []
        centerLevelNPoints = [None] * len(self.initDatas)
        initP, direct, endP = self.initArea.getPointNDirect()
        centerP = initP * 1.0
        initData = self.initDatas[0]
        #获取初始角度
        rad = direct.toRadian()
        initRot = math.degrees(rad)
        level = random.choice(initData.fishLevels)
        levelData = FISH_LEVELS_DATA[level]
        centerP = centerP + (-direct) * (levelData.width/2.0 + initData.radius)
        centerLevelNPoints[0] = (level, centerP)
        centerP = centerP + (-direct) * (levelData.width/2.0 + initData.radius)
        initData = self.initDatas[1]
        level = random.choice(initData.fishLevels)
        centerLevelNPoints[1] = (level, centerP)
        initData = self.initDatas[3]
        level = random.choice(initData.fishLevels)
        centerLevelNPoints[3] = (level, centerP)
        initData = self.initDatas[2]
        level = random.choice(initData.fishLevels)
        levelData = FISH_LEVELS_DATA[level]
        centerP = centerP + (-direct) * (levelData.width/2.0 + initData.radius)
        centerLevelNPoints[2] = (level, centerP)

        #外环大鱼
        fishLevelAmbient = random.choice([20, 21])
        levelDataAmbient = FISH_LEVELS_DATA[fishLevelAmbient]

        longestDuration = 0
        endIdx = len(self.initDatas) - 1
        for idx, initData in enumerate(self.initDatas):
            level, centerP = centerLevelNPoints[idx]
            deltaAngle = (math.pi*2)/initData.count
            levelData = FISH_LEVELS_DATA[level]
            offsetRad = math.radians(initData.offsetAngle)
            for i in xrange(initData.count):
                offsetDir = direct.rotateSelfByRadian(offsetRad + deltaAngle*i).normalize()
                startP = centerP + (offsetDir*initData.radius)
                curEndP = Point(endP.x, startP.y) + direct * (levelData.width/2.0)
                duration = curEndP.getDist(startP)/initData.speed
                #优化，把初始化位置都设到屏幕外半个身位
                realStartP = Point(initP.x, startP.y) + (-direct) * (levelData.width/2.0)
                realDuration = curEndP.getDist(realStartP)/initData.speed
                if duration > longestDuration:
                    longestDuration = duration
                self.genFishDatas.append(fish_array.FishInitData(0, level, levelData.order, initRot, \
                    realStartP.x, realStartP.y, realDuration, levelData.getMulti(), levelData.getPickedRate(), 0, \
                    pbAppendRoute([], 0, initData.speed, realDuration + TOLERATE_LAG_SECS), \
                    fish_array.FISH_ARRAY_APPEAR_TICK + (duration - realDuration)*1000))
                if idx == endIdx:
                    if i in (1, 2):
                        offsetDir = -direct
                    else:
                        offsetDir = direct
                    startP = startP + (offsetDir*self.offsetInOut)
                    curEndP = Point(endP.x, startP.y) + direct * (levelDataAmbient.width/2.0)
                    duration = curEndP.getDist(startP)/initData.speed
                    #优化，把初始化位置都设到屏幕外半个身位
                    realStartP = Point(initP.x, startP.y) + (-direct) * (levelData.width/2.0)
                    realDuration = curEndP.getDist(realStartP)/initData.speed
                    if duration > longestDuration:
                        longestDuration = duration
                    self.genFishDatas.append(fish_array.FishInitData(0, fishLevelAmbient, levelDataAmbient.order, initRot, \
                        realStartP.x, realStartP.y, realDuration, levelDataAmbient.getMulti(), levelDataAmbient.getPickedRate(), 0, \
                        pbAppendRoute([], 0, initData.speed, realDuration + TOLERATE_LAG_SECS), \
                        fish_array.FISH_ARRAY_APPEAR_TICK + (duration - realDuration)*1000))

        self.duration = longestDuration + TOLERATE_LAG_SECS
        super(FishArray, self).genFishs()

