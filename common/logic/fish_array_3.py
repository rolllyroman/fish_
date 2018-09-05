#!/usr/bin/env python
# -*- coding:utf-8 -*-

"""
Author: $Author$
Date: $Date$
Revision: $Revision$

Description:
    鱼阵3，等间距环形鱼阵
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
    def __init__(self, initArea, fishLevels, space, speed, counts):
        self.initArea = initArea
        self.fishLevels = fishLevels
        self.space = space
        self.speed = speed
        self.counts = counts

class FishArray(fish_array.FishArray):
    def __init__(self, fishMgr):
        super(FishArray, self).__init__(fishMgr)
        #基础速度
        self.speed = 54
        #每个环间鱼的间距
        self.space = -20
        self.init_areas = [
            #左边的环
            FishArrayInit(FishInitArea(Point(0, CENTER_Y), Point(0, CENTER_Y), Point(WIDTH, CENTER_Y), Point(WIDTH, CENTER_Y)), [[3], [7], [12], [16]], self.space, self.speed, [48, 30, 12, 1]), \
            #右边的环
            FishArrayInit(FishInitArea(Point(WIDTH, CENTER_Y), Point(WIDTH, CENTER_Y), Point(0, CENTER_Y), Point(0, CENTER_Y)), [[3], [7], [12], [17]], self.space, self.speed, [48, 30, 12, 1]), \
        ]

    def genFishs(self):
        self.genFishDatas = []
        centerNLevelNRadius = []
        for area in self.init_areas:
            centerP, direct, endP = area.initArea.getPointNDirect()
            count = len(area.fishLevels)
            levelNedges = []
            for i in xrange(count):
                space = self.space
                level = random.choice(area.fishLevels[i])
                levelData = FISH_LEVELS_DATA[level]
                if i == count - 1:
                    centerP = centerP + (-direct) * (levelData.width/2.0)
                    levelNedges.append((level, centerP))
                else:
                    width = levelData.width
                    if i == count - 2:
                        width = width/4.0
                        space = self.space * 2
                    elif i == 0:
                        space = self.space
                    else:
                        space = self.space / 2
                    centerP = centerP + (-direct) * (width/2.0)
                    levelNedges.append((level, centerP))
                    centerP = centerP + (-direct) * (width/2.0 + space)
            levelNRadius = []
            for level, edgeP in levelNedges:
                levelNRadius.append((level, centerP.getDist(edgeP)))
            centerNLevelNRadius.append((centerP, levelNRadius))

        longestDuration = 0
        for idx, area in enumerate(self.init_areas):
            centerP, levelNRadius = centerNLevelNRadius[idx]
            initP, direct, endP = area.initArea.getPointNDirect()
            #获取初始角度
            rad = direct.toRadian()
            initRot = math.degrees(rad)
            for i in xrange(len(levelNRadius)):
                level, radius = levelNRadius[i]
                deltaAngle = (math.pi*2)/area.counts[i]
                levelData = FISH_LEVELS_DATA[level]
                for i in xrange(area.counts[i]):
                    offsetDir = direct.rotateSelfByRadian(deltaAngle*i).normalize()
                    startP = centerP + (offsetDir*radius)
                    curEndP = Point(endP.x, startP.y) + direct * (levelData.width/2.0)
                    duration = curEndP.getDist(startP)/area.speed
                    #优化，把初始化位置都设到屏幕外半个身位
                    realStartP = Point(initP.x, startP.y) + (-direct) * (levelData.width/2.0)
                    realDuration = curEndP.getDist(realStartP)/area.speed
                    if duration > longestDuration:
                        longestDuration = duration
                    self.genFishDatas.append(fish_array.FishInitData(0, level, levelData.order, initRot, \
                        realStartP.x, realStartP.y, realDuration, levelData.getMulti(), levelData.getPickedRate(), 0, \
                        pbAppendRoute([], 0, area.speed, realDuration + TOLERATE_LAG_SECS), \
                        fish_array.FISH_ARRAY_APPEAR_TICK + (duration - realDuration)*1000))

        self.duration = longestDuration + TOLERATE_LAG_SECS
        super(FishArray, self).genFishs()

