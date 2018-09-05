#!/usr/bin/env python
# -*- coding:utf-8 -*-

"""
Author: $Author$
Date: $Date$
Revision: $Revision$

Description:
    枪类型数据
        duration                持续时间，单位秒，0表示无限时
"""

from common.gameobject import GameObject
import random

class GunType(GameObject):
    def __init__(self, type, duration):
        self.type = type
        self.duration = duration

#道具炮概率变化的上限
MAX_RATE_ITEM_GUN = 40
#道具炮出现区域
APPEAR_RATE = 0.25

#冷冻炮持续时间（单位：毫秒）
FREEZE_TICK = 2000
#冷冻炮减速比例
FREEZE_SPEED_RATE = 0.6
#翻倍跑翻倍比例
DOUBLE_COIN_RATE = 2

FREE_GUN_ODDS = 0.1
#2到6秒的免费炮
FREE_GUNS = [GunType(4, i+2) for i in xrange(5)]

GUN_TYPES_DATA = [
    #普通炮
    None, \
    #翻倍炮
    GunType(1, 10), \
    #能量炮
    GunType(2, 10), \
    #冷冻炮
    GunType(3, 10), \
    #免费炮
    #GunType(4, 5), \
]

def getFreeGun():
    return random.choice(FREE_GUNS)

def getGunType(rate):
    rateAppear = float(rate)/MAX_RATE_ITEM_GUN
    if rateAppear > 1:
        rateAppear = 1
    rateAppear = rateAppear * APPEAR_RATE
    if random.random() < rateAppear:
        return random.choice(GUN_TYPES_DATA)
    return None
