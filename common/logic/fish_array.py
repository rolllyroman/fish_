#!/usr/bin/env python
# -*- coding:utf-8 -*-

"""
Author: $Author$
Date: $Date$
Revision: $Revision$

Description:
    鱼阵基础类
"""

from common.gameobject import GameObject

FISH_ARRAY_APPEAR_SEC = 6
FISH_ARRAY_APPEAR_TICK = FISH_ARRAY_APPEAR_SEC * 1000

#from common.log import log

class FishArrayInit(GameObject):
    def __init__(self, initArea, fishLevels, speed):
        self.initArea = initArea
        self.fishLevels = fishLevels
        self.speed = speed

class FishInitData(GameObject):
    def __init__(self, idx, level, order, initRot, x, y, duration, multi, rate, dice, route, timestampOffset):
        self.idx = idx
        self.level = level
        self.order = order
        self.initRot = initRot
        self.x = x
        self.y = y
        self.duration = duration
        self.multi = multi
        self.rate = rate
        self.dice = dice
        self.route = route
        self.timestampOffset = int(timestampOffset)

class FishArray(GameObject):
    def __init__(self, fishMgr):
        #鱼阵开始时间
        self.timestampInit = 0
        #产生鱼的数据列表
        self.genFishDatas = None
        #持续时间
        self.duration = 0
        #是否开始
        self.isStarted = False
        #鱼管理类实例
        self.fishMgr = fishMgr

    def reset(self):
        #产生鱼的数据列表
        self.genFishDatas = None

    def genFishs(self):
        self.genFishDatas.sort(cmp = lambda l, r: cmp(l.timestampOffset, r.timestampOffset))
        #log(u'gen fishs finished, duration[%s]'%(self.duration))

    def start(self, timestamp):
        self.timestampInit = timestamp
        self.isStarted = True

    def stop(self):
        self.isStarted = False

    def isOver(self, timestamp):
        #log(u'timestamp[%s] initTime[%s] duration[%s] fishs[%s]'%(timestamp, self.timestampInit, self.duration, self.fishMgr.fishs))
        return self.fishMgr.isEmpty() or (timestamp - self.timestampInit) > self.duration
