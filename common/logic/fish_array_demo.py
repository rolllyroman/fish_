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

class StopFishArrayInit(GameObject): #会中途停止的鱼类
    def __init__(self, initArea, fishLevel, space, speed, stopPoint, stopTime):
        #起点终点位置，鱼编号，鱼间隔，速度，停止点，停止时间
        self.initArea = initArea
        self.fishLevel = fishLevel
        self.space = space
        self.speed = speed
        self.stopPoint = stopPoint
        self.stopTime = stopTime

class RotateFishArrayInit(GameObject): #会旋转的鱼类
    def __init__(self, initArea, fishLevel, space, speed, rotatePoint, rounds, radius, count):
        #起点终点位置，鱼编号集合，鱼间隔，速度，旋转点，旋转圈数，半径
        self.initArea = initArea
        self.fishLevel = fishLevel
        self.space = space
        self.speed = speed
        self.rotatePoint = rotatePoint
        self.rounds = rounds
        self.radius = radius
        self.count = count

class FishArray(fish_array.FishArray):
    def __init__(self, fishMgr):
        super(FishArray, self).__init__(fishMgr)
        self.init_stop_areas = [
            StopFishArrayInit(FishInitArea(Point(0, CENTER_Y), Point(0, CENTER_Y), Point(WIDTH, CENTER_Y), Point(WIDTH, CENTER_Y)), 19, 0, 120, Point(WIDTH/4, CENTER_Y), 10),
        ]
        self.init_rotate_areas = [
            RotateFishArrayInit(FishInitArea(Point(WIDTH/4*3-100, HEIGHT), Point(WIDTH/4*3-100, HEIGHT), Point(WIDTH/4*3-100, 0), Point(WIDTH/4*3-100, 0)), 1, 1, 100, Point(WIDTH/4*3-100, CENTER_Y), 1, 100, 10),
        ]

    def reset(self):
        super(FishArray, self).reset()
        self.duration = 30

    def genFishs(self):
        longestDuration = 0
        self.genFishDatas = []
        for area in self.init_stop_areas:
            level = area.fishLevel
            levelData = FISH_LEVELS_DATA[level]
            #获取出生点、方向、离终点的距离数据
            startP, direct, endP = area.initArea.getPointNDirect()
            stopP = area.stopPoint
            #获取初始角度
            rad = direct.toRadian()
            initRot = math.degrees(rad)
            #让鱼不要出现在屏幕内
            curStartP = startP + (-direct) * (levelData.width/2.0)
            curEndP = endP + direct * (levelData.width/2.0)
            #计算鱼生存时间
            duration = curEndP.getDist(curStartP)/area.speed
            #优化，把初始化位置都设到屏幕外半个身位
            realStartP = startP + (-direct) * (levelData.width/2.0)
            realDuration = curEndP.getDist(realStartP)/area.speed
            #计算到停止点的时间
            stopDuration = stopP.getDist(realStartP)/area.speed
            if duration+stopDuration > longestDuration:
                longestDuration = duration

            #节点生成
            routes = []
            pbAppendRoute(routes, 0, area.speed, stopDuration)
            pbAppendRoute(routes, 0, 0, area.stopTime)
            pbAppendRoute(routes, 0, area.speed, realDuration - stopDuration + TOLERATE_LAG_SECS)
            self.genFishDatas.append(fish_array.FishInitData(0, level, levelData.order, initRot, \
                    realStartP.x, realStartP.y, realDuration+stopDuration, levelData.getMulti(), levelData.getPickedRate(), 0, \
                    routes, fish_array.FISH_ARRAY_APPEAR_TICK + (duration - realDuration)*1000))

        for area in self.init_rotate_areas:
            level = area.fishLevel
            startP, direct, endP = area.initArea.getPointNDirect()
            rotateP = area.rotatePoint
            rad = direct.toRadian()
            initRot = math.degrees(rad)
            curStartP = startP
            for i in xrange(area.count):
                curStartP = curStartP + (-direct) * (levelData.width/2.0)
                curEndP = endP + direct * (levelData.width/2.0)
                duration = curEndP.getDist(curStartP)/area.speed
                realStartP = startP + (-direct) * (levelData.width/2.0)
                rotateDuration = rotateP.getDist(realStartP)/area.speed
                realDuration = curEndP.getDist(realStartP)/area.speed
                inRotateDuration = math.pi * area.radius * 2 * area.rounds * 1.00 / area.speed #旋转时间
                rotSpeed = int(360 * area.rounds / inRotateDuration)
                if duration+inRotateDuration > longestDuration:
                    longestDuration = duration

                routes = []
                pbAppendRoute(routes, 0, area.speed, rotateDuration)
                pbAppendRoute(routes, rotSpeed, area.speed, inRotateDuration)
                pbAppendRoute(routes, 0, area.speed, realDuration - rotateDuration - inRotateDuration + TOLERATE_LAG_SECS)
                self.genFishDatas.append(fish_array.FishInitData(0, level, levelData.order, initRot, \
                    realStartP.x, realStartP.y, realDuration+inRotateDuration, levelData.getMulti(), levelData.getPickedRate(), 0, \
                    routes, fish_array.FISH_ARRAY_APPEAR_TICK + (duration - realDuration)*1000))
                curStartP = curStartP + (-direct) * (area.space + levelData.width/2.0)

        self.duration = longestDuration + TOLERATE_LAG_SECS
        super(FishArray, self).genFishs()

