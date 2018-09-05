#!/usr/bin/env python
# -*- coding:utf-8 -*-

"""
Author: $Author$
Date: $Date$
Revision: $Revision$

Description:
    鱼阵1
"""
from common.data.scene import WIDTH, HEIGHT, CENTER_X, CENTER_Y
from common.data.fish_init_areas import FishInitArea
from common.arith.point_math import Point
from common.data.fish_levels import FISH_LEVELS_DATA
from common.data.pickfish_consts import TOLERATE_LAG_SECS
import fish_array

import random
import math

from common.pb_utils import pbAppendRoute

HORI_WAITTING_VERT_TIME = 0 #横向等待竖向时间

class FishArray(fish_array.FishArray):
    def __init__(self, fishMgr):
        super(FishArray, self).__init__(fishMgr)
        #横向队列间距
        self.spacePerHori = 300
        #横向队列移动速度
        self.speedPerHori = 72
        #竖向队列间距
        self.spacePerVert = 120
        #竖向队列移动速度
        self.speedPerVert = 144
        self.init_areas = [
            #横向第一条阵列
            fish_array.FishArrayInit(FishInitArea(Point(0 - HORI_WAITTING_VERT_TIME*self.speedPerHori, CENTER_Y-150), Point(0 - HORI_WAITTING_VERT_TIME*self.speedPerHori, CENTER_Y-150), Point(WIDTH, CENTER_Y-150), Point(WIDTH, CENTER_Y-150)), [7,7,7,10,10,10,11,11,11,13,13,13], self.speedPerHori), \
            #横向第二条阵列
            fish_array.FishArrayInit(FishInitArea(Point(-175 - HORI_WAITTING_VERT_TIME*self.speedPerHori, CENTER_Y), Point(-175 - HORI_WAITTING_VERT_TIME*self.speedPerHori, CENTER_Y), Point(WIDTH, CENTER_Y), Point(WIDTH, CENTER_Y)), [16,31,17,18], self.speedPerHori), \
            #横向第三条阵列
            fish_array.FishArrayInit(FishInitArea(Point(0 - HORI_WAITTING_VERT_TIME*self.speedPerHori, CENTER_Y+150), Point(0 - HORI_WAITTING_VERT_TIME*self.speedPerHori, CENTER_Y+150), Point(WIDTH, CENTER_Y+150), Point(WIDTH, CENTER_Y+150)), [7,7,7,10,10,10,11,11,11,13,13,13], self.speedPerHori), \
            #横向第四条阵列
            # fish_array.FishArrayInit(FishInitArea(Point(-175, 585), Point(-175, 585), Point(WIDTH, 585), Point(WIDTH, 585)), [9, 11, 15, 16, 17, 18], self.speedPerHori), \
            #竖向第一条队列
            fish_array.FishArrayInit(FishInitArea(Point(210, HEIGHT), Point(210, HEIGHT), Point(210, 0), Point(210, 0)), [3, 4, 9, 0], self.speedPerVert), \
            #竖向第二条队列
            fish_array.FishArrayInit(FishInitArea(Point(430, 0), Point(430, 0), Point(430, HEIGHT), Point(430, HEIGHT)), [3, 4, 9, 0], self.speedPerVert), \
            #竖向第三条队列
            fish_array.FishArrayInit(FishInitArea(Point(640, HEIGHT), Point(640, HEIGHT), Point(640, 0), Point(640, 0)), [3, 4, 9, 0], self.speedPerVert), \
            #竖向第四条队列
            fish_array.FishArrayInit(FishInitArea(Point(850, 0), Point(850, 0), Point(850, HEIGHT), Point(850, HEIGHT)), [3, 4, 9, 0], self.speedPerVert), \
            #竖向第五条队列
            fish_array.FishArrayInit(FishInitArea(Point(1068, HEIGHT), Point(1068, HEIGHT), Point(1068, 0), Point(1068, 0)), [3, 4, 9, 0], self.speedPerVert), \
        ]

    def reset(self):
        super(FishArray, self).reset()
        self.duration = 65

    def genFishs(self):
        longestDuration = 0
        self.genFishDatas = []
        for index, area in enumerate(self.init_areas):
            #获取出生点、方向、离终点的距离数据
            startP, direct, endP = area.initArea.getPointNDirect()
            #获取初始角度
            rad = direct.toRadian()
            initRot = math.degrees(rad)
            count = 0
            level = -1
            curStartP = startP
            i = 0
            while True:
                #获取等级，相邻不同鱼
                # fishLevels = [l for l in area.fishLevels if l != level]
                fishLevels = [l for l in area.fishLevels]
                if not fishLevels:
                    level = area.fishLevels[0]
                else:
                    # level = random.choice(fishLevels)
                    if i >= len(area.fishLevels):
                        if index in (0,1,2):
                            break
                        i = 0
                    level = area.fishLevels[i]
                    i+= 1
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
                if index in (0,2):
                    spacePerHori = self.spacePerHori / 2
                elif index == 1:
                    i2spacePerHori = [self.spacePerHori+300, self.spacePerHori+450, self.spacePerHori+650, self.spacePerHori+750]
                    spacePerHori = i2spacePerHori[i-1]
                else:
                    spacePerHori = self.spacePerHori
                self.genFishDatas.append(fish_array.FishInitData(0, level, levelData.order, initRot, \
                    realStartP.x, realStartP.y, realDuration, levelData.getMulti(), levelData.getPickedRate(), 0, \
                    pbAppendRoute([], 0, area.speed, realDuration + TOLERATE_LAG_SECS), fish_array.FISH_ARRAY_APPEAR_TICK + (duration - realDuration)*1000))
                curStartP = curStartP + (-direct) * ((spacePerHori if area.speed == self.speedPerHori else self.spacePerVert) + levelData.width/2.0)
        self.duration = longestDuration + TOLERATE_LAG_SECS
        super(FishArray, self).genFishs()

