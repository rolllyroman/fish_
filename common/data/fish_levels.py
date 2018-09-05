# -*- coding:utf-8 -*-
#!/bin/python

"""
Author: $Author$
Date: $Date$
Revision: $Revision$

Description:
FishLevels为鱼的等级配置文件，相关的数据项如下：
order               鱼的实际层次，及鱼的优先级，由1开始，越高级鱼应该越厉害
rate_appear         出现机率，此数据大部分由原来TV版移植，已经过原来街机的人调整过
limit_count         同屏最大个数，0为无限制，否则为最大个数上限
modes_count_range   鱼群模式及每次出现个数范围，个数范围用（）
                    FISH_SEQMODE_SINGLE         单体，随机自由游动
                    FISH_SEQMODE_COLONY         集群，有一个母鱼随机移动，其它集群分子会随母鱼方向及速度而变
                    FISH_SEQMODE_ONEBYONE       一条条首尾相随的鱼
                    FISH_SEQMODE_SIDEBYSIDE     一条条平行并肩的鱼
rate_pick_range     被捕获概率范围，一般不用设置，概率跟鱼的倍率有关，公式一般为 1/$鱼倍率 - $整体扣水；
                    若鱼倍率为0，比如炸弹这种道具类，则需要在此设置其被捕概率范围，($最小概率, $最大概率)，数值范围0-1。
multiple_range      倍率范围，($最小倍率, $最大倍率)，数值范围0-无穷大。
speed_range         鱼的速度范围，单位像素/秒，有两种描述形式
                    ($最小速度, $最大速度)，随机此范围内的速度值
                    [$速度值1, $速度值2, $速度值3, ...]，随机此集合内的速度值
rot_range           每次鱼速度或角度变化时的角度变化范围，单位度，有有两种描述形式
                    ($最小角度, $最大角度)，随机此范围内的角度值
                    [$角度值1, $角度值2, $角度值3, ...]，随机此集合内的角度值
rot_speed_range     角速度变化范围，单位度/秒，有两种描述形式
                    ($最小角速度, $最大角速度)，随机此范围内的角速度值
                    [$角速度1, $角速度2, $角速度3, ...]，随机此集合内的角速度值
per_time_range      每次角度或速度变化的持续时间范围，单位秒，有两种描述形式
                    ($最短秒数, $最长秒数)，随机此范围内的持续秒数
                    [$秒数1, $秒数2, $秒数3, ...]，随机此集合内的持续秒数
times_count_range   角度或速度变化的次数范围，单位次，有两种描述形式
                    ($最少次数, $最多次数)，随机此范围内的次数
                    [$次数1, $次数2, $次数3, ...]，随机此集合内的次数
width, heigth       鱼图片大小，用于生成鱼是做位置偏移，已设定完成，不用设置
seq_offset          鱼群队列间距，单位像素
min_limit_time      最小刷新间隔，单位秒，支持三位小数
max_limit_time      最大刷新间隔，单位秒，支持三位小数
max_together_count  最多同时刷几只，和鱼群模式不同，会分散刷出
"""

from common.arith.point_math import Point
from common.gameobject import GameObject
from pickfish_consts import *

import random

class FishLevel(GameObject):
    def __init__(self, order, rate_appear, limit_count, modes_count_range, \
            rate_pick_range, multiple_range, speed_range, dice_odds, \
            rot_range, rot_speed_range, per_time_range, times_count_range, \
            width, height, seq_offset, min_limit_time, max_limit_time, max_together_count):

        self.order = order
        self.rate_appear = rate_appear
        self.limit_count = limit_count
        self.modes_count_range = modes_count_range
        self.rate_pick_range = rate_pick_range
        self.multiple_range = multiple_range
        self.speed_range = speed_range
        self.dice_odds = dice_odds
        self.rot_range = rot_range
        self.rot_speed_range = rot_speed_range
        self.per_time_range = per_time_range
        self.times_count_range = times_count_range
        self.width = width
        self.height = height
        self.seq_offset = seq_offset
        self.min_limit_time = min_limit_time
        self.max_limit_time = max_limit_time
        self.max_together_count = max_together_count

    def getModeNCount(self):
        m = random.choice(self.modes_count_range.keys())
        return m, self.modes_count_range[m]

    def getPerTime(self):
        if isinstance(self.per_time_range, tuple):
            return random.randint(self.per_time_range[0], self.per_time_range[1])
        else:
            return random.choice(self.per_time_range)

    def getRotTimes(self):
        if isinstance(self.times_count_range, tuple):
            return random.randint(self.times_count_range[0], self.times_count_range[1])
        else:
            return random.choice(self.times_count_range)

    def getPickedRate(self):
        multi = self.getMulti()
        if multi:
            return 1/float(multi)
        else:
            if isinstance(self.rate_pick_range, tuple):
                return random.uniform(self.rate_pick_range[0], self.rate_pick_range[1])
            else:
                return random.choice(self.rate_pick_range)

    def getRot(self):
        if isinstance(self.rot_range, tuple):
            return random.randint(self.rot_range[0], self.rot_range[1])
        else:
            return random.choice(self.rot_range)

    def getRotSpeed(self):
        if isinstance(self.rot_speed_range, tuple):
            return random.randint(self.rot_speed_range[0], self.rot_speed_range[1])
        else:
            return random.choice(self.rot_speed_range)

    def getSpeed(self):
        if isinstance(self.speed_range, tuple):
            return random.randint(self.speed_range[0], self.speed_range[1])
        else:
            return random.choice(self.speed_range)

    def getMulti(self):
        if isinstance(self.multiple_range, tuple):
            return random.randint(self.multiple_range[0], self.multiple_range[1])
        else:
            return random.choice(self.multiple_range)

FISH_ORDER2LEVELS = {
    0 : 0,
    1 : 0,
    2 : 1,
    3 : 2,
    4 : 3,
    5 : 4,
    6 : 5,
    7 : 6,
    8 : 7,
    9 : 8,
    10 : 9,
    11 : 10,
    12 : 11,
    13 : 12,
    14 : 13,
    15 : 14,
    22 : 15,
    23 : 16,
    27 : 17,
    28 : 18,
    29 : 19,
    21 : 20,
    24 : 21,
    25 : 22,
    26 : 23,
#兼容数据，之后应弃用
    16 : 29,
    17 : 30,
    18 : 31,
    19 : 16,
    20 : 17,
}

FISH_LEVELS_DATA = [
    #level1 鱼苗
    FishLevel(
        order = 1,
        rate_appear = 0.45, 
        limit_count = 0, 
        modes_count_range = {
            FISH_SEQMODE_SINGLE :   (1,1),
            FISH_SEQMODE_COLONY :   (2,9),
        },
        rate_pick_range = (0.5, 0.5),
        multiple_range = (2,2),
        speed_range = (90,135),#(100,150), #[100,200,300,400],
        dice_odds = 0,
        rot_range = [i for i in xrange(-20, 20, 10)],
        rot_speed_range = (45, 90),
        per_time_range = [0.5,0.6,0.7,0.8,0.9,1.0,1.1,1.2,1.3,1.4,1.5,1.6,1.7,1.8,1.9,2.0],
        times_count_range = (1,3),
        width = 41,
        height = 61,
        seq_offset = 20,
        min_limit_time = 0,
        max_limit_time = 0,
        max_together_count = 0,
    ), 
    #level2 小精灵
    FishLevel(
        order = 2,
        rate_appear = 0.45, 
        limit_count = 0, 
        modes_count_range = {
            FISH_SEQMODE_SINGLE :   (1,1),
            FISH_SEQMODE_COLONY :   (2,5),
        },
        rate_pick_range = (0.33, 0.33),
        multiple_range = (3,3),
        speed_range = (110,135),#(100,150), #[100,200,300,400],
        dice_odds = 0,
        rot_range = [i for i in xrange(-20, 20, 10)],
        rot_speed_range = (45, 90),
        per_time_range = (1,4),
        times_count_range = (1,3),
        width = 59,
        height = 49,
        seq_offset = 25,
        min_limit_time = 0,
        max_limit_time = 0,
        max_together_count = 0,
    ), 
    #level3 蝴蝶鱼
    FishLevel(
        order = 3,
        rate_appear = 0.3, 
        limit_count = 0, 
        modes_count_range = {
            FISH_SEQMODE_SINGLE :   (1,1),
            FISH_SEQMODE_COLONY :   (2,4),
        },
        rate_pick_range = (0.25, 0.25),
        multiple_range = (4,4),
        speed_range = (90,135),#(100,150),
        dice_odds = 0,
        rot_range = [i for i in xrange(-90, 90, 10)],
        rot_speed_range = (30, 90),
        per_time_range = (1,4),
        times_count_range = (1,3),
        width = 68,
        height = 52,
        seq_offset = 20,
        min_limit_time = 0,
        max_limit_time = 0,
        max_together_count = 0,
    ), 
    #level4 小丑鱼
    FishLevel(
        order = 4,
        rate_appear = 0.225, 
        limit_count = 0, 
        modes_count_range = {
            FISH_SEQMODE_SINGLE :   (1,1),
            FISH_SEQMODE_ONEBYONE : (5,5),
            FISH_SEQMODE_COLONY :   (2,4),
        },
        rate_pick_range = (0.2, 0.2),
        multiple_range = (5,5),
        speed_range = (110,135),#(100,150),
        dice_odds = 0,
        rot_range = [-45, 45],
        rot_speed_range = (30, 60),
        per_time_range = (1,4),
        times_count_range = (1,3),
        width = 77,
        height = 53,
        seq_offset = 15,
        min_limit_time = 0,
        max_limit_time = 0,
        max_together_count = 0,
    ), 
    #level5 斗鱼
    FishLevel(
        order = 5,
        rate_appear = 0.18, 
        limit_count = 0, 
        modes_count_range = {
            FISH_SEQMODE_SINGLE :   (1,1),
        },
        rate_pick_range = (0.167, 0.167),
        multiple_range = (6,6),
        speed_range = (90,135),#(100,150),
        dice_odds = 0,
        rot_range = (-90, 90),
        rot_speed_range = (30, 90),
        per_time_range = (1,5),
        times_count_range = (1,3),
        width = 101,
        height = 82,
        seq_offset = 10,
        min_limit_time = 0,
        max_limit_time = 0,
        max_together_count = 0,
    ), 
    #level6 河豚
    FishLevel(
        order = 6,
        rate_appear = 0.15, 
        limit_count = 0, 
        modes_count_range = {
            FISH_SEQMODE_SINGLE :   (1,1),
        },
        rate_pick_range = (0.143, 0.143),
        multiple_range = (7,7),
        speed_range = (80,100),#(90,130),
        dice_odds = 0,
        rot_range = [i for i in xrange(-90, 90, 10)],
        rot_speed_range = (25, 75),
        per_time_range = (1,5),
        times_count_range = (1,3),
        width = 83,
        height = 86,
        seq_offset = 10,
        min_limit_time = 0,
        max_limit_time = 0,
        max_together_count = 0,
    ), 
    #level7 孔雀鱼
    FishLevel(
        order = 7,
        rate_appear = 0.1286, 
        limit_count = 0, 
        modes_count_range = {
            FISH_SEQMODE_SINGLE :   (1,1),
        },
        rate_pick_range = (0.125, 0.125),
        multiple_range = (8,8),
        speed_range = (80,100),#(90,130),
        dice_odds = 0,
        rot_range = [-180, 180],
        rot_speed_range = (30, 90),
        per_time_range = (2,5),
        times_count_range = (1,3),
        width = 144,
        height = 76,
        seq_offset = 10,
        min_limit_time = 0,
        max_limit_time = 0,
        max_together_count = 0,
    ), 
    #level8 小章鱼
    FishLevel(
        order = 8,
        rate_appear = 0.1125, 
        limit_count = 0, 
        modes_count_range = {
            FISH_SEQMODE_SINGLE :   (1,1),
        },
        rate_pick_range = (0.111, 0.111),
        multiple_range = (9,9),
        speed_range = (81,117),#(90,130),
        dice_odds = 0,
        rot_range = [i for i in xrange(-90, 90, 10)],
        rot_speed_range = (25, 75),
        per_time_range = (2,5),
        times_count_range = (2,6),
        width = 129,
        height = 65,
        seq_offset = 10,
        min_limit_time = 0,
        max_limit_time = 0,
        max_together_count = 0,
    ), 
    #level9 荧水母
    FishLevel(
        order = 9,
        rate_appear = 0.1, 
        limit_count = 0, 
        modes_count_range = {
            FISH_SEQMODE_SINGLE :   (1,1),
        },
        rate_pick_range = (0.1, 0.1),
        multiple_range = (10,10),
        speed_range = (25,50),#(90,130),
        dice_odds = 0,
        rot_range = (-90, 90),
        rot_speed_range = (45, 75),
        per_time_range = (2,6),
        times_count_range = (2,6),
        width = 124,
        height = 178,
        seq_offset = 10,
        min_limit_time = 0,
        max_limit_time = 0,
        max_together_count = 0,
    ), 
    #level10 灯笼鱼
    FishLevel(
        order = 10,
        rate_appear = 0.09, 
        limit_count = 0, 
        modes_count_range = {
            FISH_SEQMODE_SINGLE :   (1,1),
        },
        rate_pick_range = (0.083, 0.083),
        multiple_range = (12,12),
        speed_range = (60,110),#(90,130),
        dice_odds = 0,
        rot_range = (-30, 30),
        rot_speed_range = (60, 90),
        per_time_range = (2,6),
        times_count_range = (1,3),
        width = 135,
        height = 95,
        seq_offset = 2,
        min_limit_time = 0,
        max_limit_time = 0,
        max_together_count = 0,
    ), 
    #level11 蝙蝠鱼
    FishLevel(
        order = 11,
        rate_appear = 0.075, 
        limit_count = 0, 
        modes_count_range = {
            FISH_SEQMODE_SINGLE :   (1,1),
            FISH_SEQMODE_ONEBYONE : (5,5),
        },
        rate_pick_range = (0.071, 0.071),
        multiple_range = (14,14),
        speed_range = (95,120),#(80,120),
        dice_odds = 0,
        rot_range = (-60, 60),
        rot_speed_range = (20, 60),
        per_time_range = (1,4),
        times_count_range = (1,2),
        width = 215,
        height = 199,
        seq_offset = 20,
        min_limit_time = 0,
        max_limit_time = 0,
        max_together_count = 0,
    ), 
    #level12 剑鱼
    FishLevel(
        order = 12,
        rate_appear = 0.06, 
        limit_count = 0, 
        modes_count_range = {
            FISH_SEQMODE_SINGLE :   (1,1),
        },
        rate_pick_range = (0.063, 0.063),
        multiple_range = (16,16),
        speed_range = (100,120),#(80,120),
        dice_odds = 0,
        rot_range = (-60, 60),
        rot_speed_range = (30, 60),
        per_time_range = (2,6),
        times_count_range = (1,2),
        width = 311,
        height = 149,
        seq_offset = 10,
        min_limit_time = 0,
        max_limit_time = 0,
        max_together_count = 0,
    ), 
    #level13 紫夜蝠
    FishLevel(
        order = 13,
        rate_appear = 0.05, 
        limit_count = 2, 
        modes_count_range = {
            FISH_SEQMODE_SINGLE :   (1,1),
        },
        rate_pick_range = (0.055, 0.055),
        multiple_range = (20,20),
        speed_range = (95,120),#(70,100),
        dice_odds = 0,
        rot_range = (-60, 60),
        rot_speed_range = (30, 60),
        per_time_range = (2,6),
        times_count_range = (1,2),
        width = 254,
        height = 264,
        seq_offset = 10,
        min_limit_time = 0,
        max_limit_time = 0,
        max_together_count = 0,
    ), 
    #level14 银鲨
    FishLevel(
        order = 14,
        rate_appear = 0.045, 
        limit_count = 3, 
        modes_count_range = {
            FISH_SEQMODE_SINGLE :   (1,1),
        },
        rate_pick_range = (0.044, 0.044),
        multiple_range = (25,25),
        speed_range = (63,90),#(70,100),
        dice_odds = 0,
        rot_range = (-30, 30),
        rot_speed_range = (35, 45),
        per_time_range = (2,6),
        times_count_range = (1,3),
        width = 279,
        height = 144,
        seq_offset = 10,
        min_limit_time = 5,
        max_limit_time = 5,
        max_together_count = 2,
    ), 
    #level15 魔鲸
    FishLevel(
        order = 15,
        rate_appear = 0.03, 
        limit_count = 1, 
        modes_count_range = {
            FISH_SEQMODE_SINGLE :   (1,1),
        },
        rate_pick_range = (0.04, 0.04),
        multiple_range = (30,30),
        speed_range = (54,63),#(60,70),
        dice_odds = 0,
        rot_range = (0, 0),
        rot_speed_range = (30, 35),
        per_time_range = (2,6),
        times_count_range = (0,0),
        width = 472,
        height = 240,
        seq_offset = 10,
        min_limit_time = 0,
        max_limit_time = 0,
        max_together_count = 0,
    ), 
    #level16 金龟
    FishLevel(
        order = 22,
        rate_appear = 0.0225, 
        limit_count = 3, 
        modes_count_range = {
            FISH_SEQMODE_SINGLE :   (1,1),
        },
        rate_pick_range = (0.031, 0.031),
        multiple_range = (35,35),
        speed_range = (45,63),#(50,70),
        dice_odds = 0,
        rot_range = (-15, 15),
        rot_speed_range = (25, 25),
        per_time_range = (2,6),
        times_count_range = (2,4),
        width = 159,
        height = 180,
        seq_offset = 10,
        min_limit_time = 5,
        max_limit_time = 5,
        max_together_count = 0,
    ), 
    #level17 金鲨
    FishLevel(
        order = 23,
        rate_appear = 0.0225, 
        limit_count = 1, 
        modes_count_range = {
            FISH_SEQMODE_SINGLE :   (1,1),
        },
        rate_pick_range = (0.028, 0.028),
        multiple_range = (40,40),
        speed_range = (70,110),#(60,70),
        dice_odds = 0,
        rot_range = (-10, 10),
        rot_speed_range = (20, 20),
        per_time_range = (3,8),
        times_count_range = (1,2),
        width = 336,
        height = 183,
        seq_offset = 10,
        min_limit_time = 10,
        max_limit_time = 10,
        max_together_count = 0,
    ), 
    #level18 黄金甲
    FishLevel(
        order = 27,
        rate_appear = 0.0045, 
        limit_count = 1, 
        modes_count_range = {
            FISH_SEQMODE_SINGLE :   (1,1),
        },
        rate_pick_range = (0.022, 0.022),
        multiple_range = (50,50),
        speed_range = (70,110),#(60,70),
        dice_odds = 0,
        rot_range = (-10, 10),
        rot_speed_range = (15, 15),
        per_time_range = (3,8),
        times_count_range = (1,2),
        width = 365,
        height = 202,
        seq_offset = 10,
        min_limit_time = 0,
        max_limit_time = 0,
        max_together_count = 0,
    ), 
    #level19 赤金龙
    FishLevel(
        order = 28,
        rate_appear = 0.0225, 
        limit_count = 2, 
        modes_count_range = {
            FISH_SEQMODE_SINGLE :   (1,1),
        },
        rate_pick_range = (0.014, 0.014),
        multiple_range = (80,80),
        speed_range = (65,90),#(40,50),
        dice_odds = 0,
        rot_range = (0, 0),
        rot_speed_range = (10, 10),
        per_time_range = (3,8),
        times_count_range = (0,0),
        width = 537,
        height = 170,
        seq_offset = 10,
        min_limit_time = 20,
        max_limit_time = 30,
        max_together_count = 0,
    ), 
    #level20,深海鱼雷
    FishLevel(
        order = 29,
        rate_appear = 0.01, 
        limit_count = 1, 
        modes_count_range = {
            FISH_SEQMODE_SINGLE :   (1,1),
        },
        rate_pick_range = (0.005,0.005),
        multiple_range = (0,0),
        speed_range = (54,84),#(40,50),
        dice_odds = 0,
        rot_range = [-30, 30],
        rot_speed_range = (5, 10),
        per_time_range = (10, 15),
        times_count_range = (0,1),
        width = 363,
        height = 373,
        seq_offset = 10,
        min_limit_time = 120,
        max_limit_time = 160,
        max_together_count = 0,
    ), 
    #level21,大盘鱼1小三元
    FishLevel(
        order = 21,
        rate_appear = 0.03, 
        limit_count = 1, 
        modes_count_range = {
            FISH_SEQMODE_SINGLE :   (1,1),
        },
        rate_pick_range = (0.023, 0.023),
        multiple_range = (60,60),
        speed_range = (60,80),#(60,70),
        dice_odds = 0,
        rot_range = (-5, 5),
        rot_speed_range = (10, 10),
        per_time_range = (3,8),
        times_count_range = (2,4),
        width = 150,
        height = 150,
        seq_offset = 10,
        min_limit_time = 0,
        max_limit_time = 0,
        max_together_count = 0,
    ),
    #level22,大盘鱼2大三元
    FishLevel(
        order = 24,
        rate_appear = 0.03, 
        limit_count = 1, 
        modes_count_range = {
            FISH_SEQMODE_SINGLE :   (1,1),
        },
        rate_pick_range = (0.022, 0.022),
        multiple_range = (65,65),
        speed_range = (60,80),#(60,70),
        dice_odds = 0,
        rot_range = (-5, 5),
        rot_speed_range = (10, 10),
        per_time_range = (3,8),
        times_count_range = (2,4),
        width = 150,
        height = 150,
        seq_offset = 10,
        min_limit_time = 0,
        max_limit_time = 0,
        max_together_count = 0,
    ), 
    #level23,大盘鱼3小四喜
    FishLevel(
        order = 25,
        rate_appear = 0.0225, 
        limit_count = 1, 
        modes_count_range = {
            FISH_SEQMODE_SINGLE :   (1,1),
        },
        rate_pick_range = (0.022, 0.022),
        multiple_range = (70,70),
        speed_range = (60,80),
        dice_odds = 0,
        rot_range = (-5, 5),
        rot_speed_range = (10, 10),
        per_time_range = (3,8),
        times_count_range = (2,4),
        width = 150,
        height = 150,
        seq_offset = 10,
        min_limit_time = 0,
        max_limit_time = 0,
        max_together_count = 0,
    ), 
    #level24,大盘鱼4
    FishLevel(
        order = 26,
        rate_appear = 0.018, 
        limit_count = 1, 
        modes_count_range = {
            FISH_SEQMODE_SINGLE :   (1,1),
        },
        rate_pick_range = (0.022, 0.022),
        multiple_range = (75,75),
        speed_range = (60,80),#(60,70),
        dice_odds = 0,
        rot_range = (-5, 5),
        rot_speed_range = (10, 10),
        per_time_range = (3,8),
        times_count_range = (2,4),
        width = 150,
        height = 150,
        seq_offset = 10,
        min_limit_time = 0,
        max_limit_time = 0,
        max_together_count = 0,
    ), 
    #level25,比目鱼1
    FishLevel(
        order = 14,
        rate_appear = 0, 
        limit_count = 0, 
        modes_count_range = {
            FISH_SEQMODE_SINGLE :   (1,1),
        },
        rate_pick_range = (0.0045, 0.0045),
        multiple_range = (20,20),
        speed_range = (54,63),#(60,70),
        dice_odds = 0,
        rot_range = (-5, 5),
        rot_speed_range = (10, 10),
        per_time_range = (3,8),
        times_count_range = (2,4),
        width = 132,
        height = 118,
        seq_offset = 10,
        min_limit_time = 0,
        max_limit_time = 0,
        max_together_count = 0,
    ), 
    #level26,蝙蝠鱼1
    FishLevel(
        order = 15,
        rate_appear = 0, 
        limit_count = 0, 
        modes_count_range = {
            FISH_SEQMODE_SINGLE :   (1,1),
        },
        rate_pick_range = (0.0045, 0.0045),
        multiple_range = (30,30),
        speed_range = (54,63),#(60,70),
        dice_odds = 0,
        rot_range = (-5, 5),
        rot_speed_range = (10, 10),
        per_time_range = (3,8),
        times_count_range = (2,4),
        width = 132,
        height = 118,
        seq_offset = 10,
        min_limit_time = 0,
        max_limit_time = 0,
        max_together_count = 0,
    ),  
    #level27,金海豚1
    FishLevel(
        order = 22,
        rate_appear = 0, 
        limit_count = 0, 
        modes_count_range = {
            FISH_SEQMODE_SINGLE :   (1,1),
        },
        rate_pick_range = (0.0045, 0.0045),
        multiple_range = (40,40),
        speed_range = (54,63),#(60,70),
        dice_odds = 0,
        rot_range = (-5, 5),
        rot_speed_range = (10, 10),
        per_time_range = (3,8),
        times_count_range = (2,4),
        width = 132,
        height = 118,
        seq_offset = 10,
        min_limit_time = 0,
        max_limit_time = 0,
        max_together_count = 0,
    ), 
    #level28,银鲨鱼1
    FishLevel(
        order = 23,
        rate_appear = 0, 
        limit_count = 0, 
        modes_count_range = {
            FISH_SEQMODE_SINGLE :   (1,1),
        },
        rate_pick_range = (0.0045, 0.0045),
        multiple_range = (40,40),
        speed_range = (54,63),#(60,70),
        dice_odds = 0,
        rot_range = (-5, 5),
        rot_speed_range = (10, 10),
        per_time_range = (3,8),
        times_count_range = (2,4),
        width = 132,
        height = 118,
        seq_offset = 10,
        min_limit_time = 0,
        max_limit_time = 0,
        max_together_count = 0,
    ), 
    #level29,金鲨鱼1
    FishLevel(
        order = 27,
        rate_appear = 0, 
        limit_count = 0, 
        modes_count_range = {
            FISH_SEQMODE_SINGLE :   (1,1),
        },
        rate_pick_range = (0.0045, 0.0045),
        multiple_range = (200,200),
        speed_range = (54,63),#(60,70),
        dice_odds = 0,
        rot_range = (-5, 5),
        rot_speed_range = (10, 10),
        per_time_range = (3,8),
        times_count_range = (2,4),
        width = 132,
        height = 118,
        seq_offset = 10,
        min_limit_time = 0,
        max_limit_time = 0,
        max_together_count = 0,
    ), 
    #level30,宝箱
    FishLevel(
        order = 16,
        rate_appear = 0.0225, 
        limit_count = 1, 
        modes_count_range = {
            FISH_SEQMODE_SINGLE :   (1,1),
        },
        rate_pick_range = (0.028, 0.028),
        multiple_range = (20,60),
        speed_range = (54,63),#(60,70),
        dice_odds = 0,
        rot_range = (-5, 5),
        rot_speed_range = (10, 10),
        per_time_range = (3,8),
        times_count_range = (2,8),
        width = 134,
        height = 127,
        seq_offset = 10,
        min_limit_time = 0,
        max_limit_time = 0,
        max_together_count = 0,
    ), 
    #level31,聚宝龙龟
    FishLevel(
        order = 17,
        rate_appear = 0.0225, 
        limit_count = 1, 
        modes_count_range = {
            FISH_SEQMODE_SINGLE :   (1,1),
        },
        rate_pick_range = (0.02, 0.02),
        multiple_range = (55,55),
        speed_range = (65,75),#(60,70),
        dice_odds = 0,
        rot_range = (0, 0),
        rot_speed_range = (10, 10),
        per_time_range = (3,8),
        times_count_range = (0,0),
        width = 460,
        height = 337,
        seq_offset = 10,
        min_limit_time = 60,
        max_limit_time = 80,
        max_together_count = 0,
    ), 
    #level32,大金蟾
    FishLevel(
        order = 18,
        rate_appear = 0.0225, 
        limit_count = 1, 
        modes_count_range = {
            FISH_SEQMODE_SINGLE :   (1,1),
        },
        rate_pick_range = (0.006, 0.006),
        multiple_range = (100,250),
        speed_range = (65,75),#(60,70),
        dice_odds = 0,
        rot_range = (0, 0),
        rot_speed_range = (10, 10),
        per_time_range = (3,8),
        times_count_range = (0,0),
        width = 480,
        height = 364,
        seq_offset = 10,
        min_limit_time = 0,
        max_limit_time = 0,
        max_together_count = 0,
    ), 
    #level33,金算盘（免费炮弹）
    FishLevel(
        order = 0,
        rate_appear = 0.0225, 
        limit_count = 1, 
        modes_count_range = {
            FISH_SEQMODE_SINGLE :   (1,1),
        },
        rate_pick_range = (0.06, 0.06),
        multiple_range = (20,20),
        speed_range = (70,90),#(60,70),
        dice_odds = 0,
        rot_range = (-5, 5),
        rot_speed_range = (10, 10),
        per_time_range = (3,8),
        times_count_range = (2,8),
        width = 217,
        height = 120,
        seq_offset = 10,
        min_limit_time = 60,
        max_limit_time = 60,
        max_together_count = 0,
    ), 
    #level34,冰冻鱼
    FishLevel(
        order = 0,
        rate_appear = 0.026, 
        limit_count = 1, 
        modes_count_range = {
            FISH_SEQMODE_SINGLE :   (1,1),
        },
        rate_pick_range = (0.02, 0.02),
        multiple_range = (50,50),
        speed_range = (65,75),#(60,70),
        dice_odds = 0,
        rot_range = (0, 0),
        rot_speed_range = (10, 10),
        per_time_range = (3,8),
        times_count_range = (0,0),
        width = 480,
        height = 364,
        seq_offset = 10,
        min_limit_time = 0,
        max_limit_time = 0,
        max_together_count = 0,
    ),
    #level35,红包鱼
    FishLevel(
        order = 0,
        rate_appear = 0.026,
        limit_count = 1,
        modes_count_range = {
            FISH_SEQMODE_SINGLE :   (1,1),
        },
        rate_pick_range = (0.06, 0.06),
        multiple_range = (0,0),
        speed_range = (65,75),#(60,70),
        dice_odds = 0,
        rot_range = (0, 0),
        rot_speed_range = (10, 10),
        per_time_range = (3,8),
        times_count_range = (0,0),
        width = 480,
        height = 364,
        seq_offset = 10,
        min_limit_time = 0,
        max_limit_time = 0,
        max_together_count = 0,
    ),
]

class FishLevelsLimit(GameObject): #多条鱼限制
    def __init__(self, fishLevels, limit_count, min_limit_time, max_limit_time, death_min_limit_time, death_max_limit_time):
        self.fishLevels = fishLevels
        self.limit_count = limit_count
        self.min_limit_time = min_limit_time
        self.max_limit_time = max_limit_time
        self.death_min_limit_time = death_min_limit_time
        self.death_max_limit_time = death_max_limit_time

FISH_LEVELS_LIMIT_DATA = [
    FishLevelsLimit(
        fishLevels = (20,21,22,23),
        limit_count = 2,
        min_limit_time = 0,
        max_limit_time = 0,
        death_min_limit_time = 2 * 60,
        death_max_limit_time = 5 * 60,
    ), 
    FishLevelsLimit(
        fishLevels = (30,31),
        limit_count = 1,
        min_limit_time = 60,
        max_limit_time = 80,
        death_min_limit_time = 0,
        death_max_limit_time = 0,
    ), 
]

