#!/usr/bin/env python
# -*- coding:utf-8 -*-

"""
Author: $Author$
Date: $Date$
Revision: $Revision$

Description:
    鱼阵4，中间定时圆形出鱼
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
    def __init__(self, fishLevels, speed, count, time):
        self.fishLevels = fishLevels
        self.speed = speed
        self.count = count
        self.time = time

class FishArray(fish_array.FishArray):
    def __init__(self, fishMgr):
        super(FishArray, self).__init__(fishMgr)
        #基础速度
        self.speed = 90
        #每个环间鱼的间距
        self.interval = 2
        self.initArea = FishInitArea(Point(CENTER_X, CENTER_Y), Point(CENTER_X, CENTER_Y), Point(WIDTH, CENTER_Y), Point(WIDTH, CENTER_Y))
        self.initDatas = [
            #第1批
            FishArrayInit([0], self.speed, 18, 3.5), \
            #第2批
            FishArrayInit([1], self.speed, 18, 3.5), \
            #第3批
            FishArrayInit([0], self.speed, 18, 3.5), \
            #第4批
            FishArrayInit([2], self.speed, 18, 3.5), \
            #第5批
            FishArrayInit([3], self.speed, 18, 3.5), \
            #第6批
            FishArrayInit([5], self.speed, 18, 3.5), \
            #第7批
            FishArrayInit([3], self.speed, 18, 3.5), \
            #第8批
            FishArrayInit([8], self.speed, 12, 3.5), \
            #第9批
            FishArrayInit([15], self.speed, 12, 3.5), \
        ]
        self.dataIdx = 0
        self.longDist = math.sqrt((WIDTH**2) + (HEIGHT**2))/2

    def genFishs(self):
        self.genFishDatas = []
        for idx, initData in enumerate(self.initDatas):
            level = random.choice(initData.fishLevels)
            levelData = FISH_LEVELS_DATA[level]
            startP, direct, endP = self.initArea.getPointNDirect()
            deltaAngle = (math.pi*2)/initData.count
            self.duration = (self.longDist/initData.speed) + initData.time
            for i in xrange(initData.count):
                curDir = direct.rotateSelfByRadian(deltaAngle*i).normalize()
                #获取初始角度
                rad = curDir.toRadian()
                initRot = math.degrees(rad)
                self.genFishDatas.append(fish_array.FishInitData(0, level, levelData.order, initRot, \
                    startP.x, startP.y, self.duration, levelData.getMulti(), levelData.getPickedRate(), 0, \
                     pbAppendRoute([], 0, initData.speed, self.duration + TOLERATE_LAG_SECS), \
                     fish_array.FISH_ARRAY_APPEAR_TICK + idx * self.interval * 1000))
            self.dataIdx += 1
            self.duration += idx * self.interval + TOLERATE_LAG_SECS
        super(FishArray, self).genFishs()


