#!/usr/bin/env python
# -*- coding:utf-8 -*-

"""
Author: $Author$
Date: $Date$
Revision: $Revision$

Description:
    鱼阵5，外面4排中间一大堆
"""
from common.data.scene import WIDTH, HEIGHT, CENTER_X, CENTER_Y
from common.data.fish_init_areas import FishInitArea
from common.arith.point_math import Point
from common.data.fish_levels import FISH_LEVELS_DATA
from common.data.pickfish_consts import TOLERATE_LAG_SECS
from common.gameobject import GameObject
import fish_array

import random
import math
import copy

from common.pb_utils import pbAppendRoute

WINDTH_AROUND = 186
WINDTH_LNR = 50

class FishArrayInit(GameObject):
    def __init__(self, initArea, fishLevels, spaces, speed, counts):
        #先传纵向再传横向
        self.initArea = initArea
        self.fishLevels = fishLevels
        self.spaces = spaces
        self.speed = speed
        self.counts = counts

class FishArray(fish_array.FishArray):
    def __init__(self, fishMgr):
        super(FishArray, self).__init__(fishMgr)
        #左到右队列间距
        self.L2RPerHori = 14
        #左到右队列移动速度
        self.L2RSpeedPerVert = 144
        #右到左队列间距
        self.R2LPerHori = 24
        #右到左队列移动速度
        self.R2LSpeedPerVert = 144
        self.init_areas = [
            #右到左第一条阵列
            fish_array.FishArrayInit(FishInitArea(Point(WIDTH, CENTER_Y+WINDTH_AROUND+WINDTH_LNR), Point(WIDTH, CENTER_Y+WINDTH_AROUND+WINDTH_LNR), Point(0, CENTER_Y+WINDTH_AROUND+WINDTH_LNR), Point(0, CENTER_Y+WINDTH_AROUND+WINDTH_LNR)), [3], self.R2LSpeedPerVert), \
            #左到右第一条阵列
            fish_array.FishArrayInit(FishInitArea(Point(0, CENTER_Y+WINDTH_AROUND), Point(0, CENTER_Y+WINDTH_AROUND), Point(WIDTH, CENTER_Y+WINDTH_AROUND), Point(WIDTH, CENTER_Y+WINDTH_AROUND)), [0], self.L2RSpeedPerVert), \
            #左到右第二条阵列
            fish_array.FishArrayInit(FishInitArea(Point(0, CENTER_Y-WINDTH_AROUND), Point(0, CENTER_Y-WINDTH_AROUND), Point(WIDTH, CENTER_Y-WINDTH_AROUND), Point(WIDTH, CENTER_Y-WINDTH_AROUND)), [0], self.L2RSpeedPerVert), \
            #右到左第二条阵列
            fish_array.FishArrayInit(FishInitArea(Point(WIDTH, CENTER_Y-WINDTH_AROUND-WINDTH_LNR), Point(WIDTH, CENTER_Y-WINDTH_AROUND-WINDTH_LNR), Point(0, CENTER_Y-WINDTH_AROUND-WINDTH_LNR), Point(0, CENTER_Y-WINDTH_AROUND-WINDTH_LNR)), [3], self.R2LSpeedPerVert), \
        ]
        for i, areaData in enumerate(self.init_areas):
            if i in (0,3):
                areaData.spacePerHori = self.R2LPerHori
            else:
                areaData.spacePerHori = self.L2RPerHori
        self.other_init_areas = [
            FishArrayInit(FishInitArea(Point(0, CENTER_Y), Point(0, CENTER_Y), Point(WIDTH, CENTER_Y), Point(WIDTH, CENTER_Y)), [11], [18/2,0], self.L2RSpeedPerVert/2, [2,1]), \
            FishArrayInit(FishInitArea(Point(-CENTER_X+80, CENTER_Y), Point(-CENTER_X+80, CENTER_Y), Point(WIDTH, CENTER_Y), Point(WIDTH, CENTER_Y)), [2], [30,250], self.L2RSpeedPerVert/2, [3,2]), \
            FishArrayInit(FishInitArea(Point(-CENTER_X+80, CENTER_Y), Point(-CENTER_X+80, CENTER_Y), Point(WIDTH, CENTER_Y), Point(WIDTH, CENTER_Y)), [2], [80,35], self.L2RSpeedPerVert/2, [2,7]), \
            FishArrayInit(FishInitArea(Point(-CENTER_X+310, CENTER_Y), Point(-CENTER_X+310, CENTER_Y), Point(WIDTH, CENTER_Y), Point(WIDTH, CENTER_Y)), [18], [0,0], self.L2RSpeedPerVert/2, [1,1]), \
            FishArrayInit(FishInitArea(Point(-WIDTH+350, CENTER_Y), Point(-WIDTH+350, CENTER_Y), Point(WIDTH, CENTER_Y), Point(WIDTH, CENTER_Y)), [15], [0,0], self.L2RSpeedPerVert/2, [1,1]), \
            FishArrayInit(FishInitArea(Point(-WIDTH+235, CENTER_Y), Point(-WIDTH+235, CENTER_Y), Point(WIDTH, CENTER_Y), Point(WIDTH, CENTER_Y)), [9], [50,0], self.L2RSpeedPerVert/2, [2,1]), \
        ]

    def reset(self):
        super(FishArray, self).reset()
        self.duration = 30

    def genFishs(self):
        longestDuration = 0
        self.genFishDatas = []
        for area in self.init_areas:
            #获取出生点、方向、离终点的距离数据
            startP, direct, endP = area.initArea.getPointNDirect()
            #获取初始角度
            rad = direct.toRadian()
            initRot = math.degrees(rad)
            count = 0
            level = -1
            curStartP = startP
            while True:
                #获取等级，相邻不同鱼
                fishLevels = [l for l in area.fishLevels if l != level]
                if not fishLevels:
                    level = area.fishLevels[0]
                else:
                    level = random.choice(fishLevels)
                levelData = FISH_LEVELS_DATA[level]
                #让鱼不要出现在屏幕内
                curStartP = curStartP + (-direct) * (levelData.width/2.0)
                curEndP = endP + direct * (levelData.width/2.0)
                #计算鱼生存时间
                duration = curEndP.getDist(curStartP)/area.speed
                #print "start[%s, %s] end[%s, %s] speed[%s] dist[%s] duration[%s]"%(curStartP.x, curStartP.y, \
                #    curEndP.x, curEndP.y, area.speed, dist, duration)
                #计算生成时间
                durationGen = curStartP.getDist(startP)/area.speed
                if durationGen > self.duration:
                    break
                #优化，把初始化位置都设到屏幕外半个身位
                realStartP = startP + (-direct) * (levelData.width/2.0)
                realDuration = curEndP.getDist(realStartP)/area.speed
                if duration > longestDuration:
                    longestDuration = duration
                self.genFishDatas.append(fish_array.FishInitData(0, level, levelData.order, initRot, \
                    realStartP.x, realStartP.y, realDuration, levelData.getMulti(), levelData.getPickedRate(), 0, \
                    pbAppendRoute([], 0, area.speed, realDuration + TOLERATE_LAG_SECS), fish_array.FISH_ARRAY_APPEAR_TICK + (duration - realDuration)*1000))
                curStartP = curStartP + (-direct) * (area.spacePerHori + levelData.width/2.0)
        for area in self.other_init_areas:
            startP, direct, endP = area.initArea.getPointNDirect()
            rad = direct.toRadian()
            initRot = math.degrees(rad)
            level = random.choice(area.fishLevels)
            levelData = FISH_LEVELS_DATA[level]
            count4height, count4width = area.counts
            space4height, space4width = area.spaces
            startPs = []
            #纵向鱼生成
            startP4Hs = []
            if count4height%2:
                startP4Hs.append((startP, direct, endP))
            for i in xrange(count4height/2):
                addLen = (i + 1) * (levelData.height/2.0 + space4height)
                realStartP = copy.deepcopy(startP)
                realStartP.y += addLen
                realEndP = copy.deepcopy(endP)
                realEndP.y += addLen
                startP4Hs.append((realStartP, direct, realEndP))
                realStartP = copy.deepcopy(startP)
                realStartP.y -= addLen
                realEndP = copy.deepcopy(endP)
                realEndP.y -= addLen
                startP4Hs.append((realStartP, direct, realEndP))
            #横向鱼生成
            if count4width%2:
                startPs.extend(startP4Hs)
            for i in xrange(count4width/2):
                addLen = (i + 1) * (levelData.width/2.0 + space4width)
                for _startP, _direct, _endP in startP4Hs:
                    realStartP = copy.deepcopy(_startP)
                    realStartP.x += addLen
                    startPs.append((realStartP, _direct, realEndP))
                    realStartP = copy.deepcopy(_startP)
                    realStartP.x -= addLen
                    startPs.append((realStartP, _direct, realEndP))
            for fishData in startPs:
                #让鱼不要出现在屏幕内
                startP, direct, endP = fishData
                curStartP = startP + (-direct) * (levelData.width/2.0)
                curEndP = endP + direct * (levelData.width/2.0)
                #计算鱼生存时间
                duration = curEndP.getDist(curStartP)/area.speed
                #计算生成时间
                durationGen = curStartP.getDist(startP)/area.speed
                #优化，把初始化位置都设到屏幕外半个身位
                realStartP = startP + (-direct) * (levelData.width/2.0)
                realDuration = curEndP.getDist(realStartP)/area.speed
                if duration > longestDuration:
                    longestDuration = duration
                self.genFishDatas.append(fish_array.FishInitData(0, level, levelData.order, initRot, \
                    realStartP.x, realStartP.y, realDuration, levelData.getMulti(), levelData.getPickedRate(), 0, \
                    pbAppendRoute([], 0, area.speed, realDuration + TOLERATE_LAG_SECS), fish_array.FISH_ARRAY_APPEAR_TICK + (duration - realDuration)*1000))
        self.duration = longestDuration + TOLERATE_LAG_SECS
        super(FishArray, self).genFishs()

