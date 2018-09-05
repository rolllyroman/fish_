#!/usr/bin/env python
# -*- coding:utf-8 -*-

"""
Author: $Author$
Date: $Date$
Revision: $Revision$

Description:
    鱼阵预生成
"""
import random
from common.log import log

from common.gameobject import GameObject

from common import fish_data_pb2
from common.data.fish_levels import FISH_LEVELS_DATA
from common.pb_utils import pbAppendFishesData

import fish_array
import fish_array_1
import fish_array_2
import fish_array_3
import fish_array_4
import fish_array_5

FISH_GEN_FILENAME = 'fish_array'

class FishArrayData(GameObject):
    def __init__(self, duration, fishDatas):
        self.duration = duration
        self.fishDatas = fishDatas

class FishArrayGenerator(GameObject):
    def __init__(self, maxSampleCounts = (1, 1, 1, 1, 1)):
        self.fishArrays = (
            fish_array_1.FishArray(None), \
            fish_array_2.FishArray(None), \
            fish_array_3.FishArray(None), \
            fish_array_4.FishArray(None), \
            fish_array_5.FishArray(None), \
        )

        assert len(maxSampleCounts) == len(self.fishArrays)
        self.maxSampleCounts = maxSampleCounts

        self.fishArrayDatas = []
        self.getNum = 0

    def getFishData(self):
        # return random.choice(self.fishArrayDatas)
        self.getNum += 1
        if self.getNum >= len(self.fishArrayDatas):
            self.getNum = 0
        return self.fishArrayDatas[self.getNum]

    def generate(self):
        for count, fishArray in zip(self.maxSampleCounts, self.fishArrays):
            for i in xrange(count):
                fishArray.reset()
                fishArray.genFishs()
                self.fishArrayDatas.append(FishArrayData(int(fishArray.duration * 1000), fishArray.genFishDatas))

    def save(self):
        """
        """
        fishesProto = fish_data_pb2.FishArrays()
        for fishesData in self.fishArrayDatas:
            fishArray = fishesProto.fishArrays.add()
            fishArray.duration = fishesData.duration
            pbAppendFishesData(fishArray.fishes, fishesData.fishDatas)

        f = open(FISH_GEN_FILENAME, 'wb')
        f.write(fishesProto.SerializeToString())
        f.close()

    def saveC(self):
        """
        """
        fishesProto = fish_data_pb2.FishesData()
        for fishesData in self.fishArrayDatas:
            pbAppendFishesData(fishesProto.fishes, fishesData.fishDatas)

        f = open(FISH_GEN_FILENAME + '_c', 'wb')
        f.write(fishesProto.SerializeToString())
        f.close()

        f = open('fish_data_c/' + FISH_GEN_FILENAME + '_c.bin', 'wb')
        f.write(fishesProto.SerializeToString())
        f.close()

    def load(self):
        """
        """
        fishesProto = fish_data_pb2.FishArrays()
        f = open(FISH_GEN_FILENAME, 'rb')
        fishesProto.ParseFromString(f.read())
        f.close()

        idx = 0
        for fishArray in fishesProto.fishArrays:
            fishDatas = []
            for fish in fishArray.fishes:
                levelData = FISH_LEVELS_DATA[fish.level]
                fishDatas.append(fish_array.FishInitData(idx, fish.level, levelData.order, fish.rot, \
                    fish.x, fish.y, fish.duration, levelData.getMulti(), levelData.getPickedRate(), 0, \
                    None, fish.offset))
                idx += 1
            self.fishArrayDatas.append(FishArrayData(fishArray.duration, fishDatas))
