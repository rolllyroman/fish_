#!/usr/bin/env python
# -*- coding:utf-8 -*-

"""
@Author: $Author$
@Date: $Date$
@version: $Revision$

Description:
    鱼和鱼阵批量文件生成脚本
"""

from common.logic.fish_generator import FishGenerator
from common.logic.fish_array_generator import FishArrayGenerator

if __name__ == '__main__':
    #鱼预生成，每种鱼生成200条数据
    fishGenerator = FishGenerator(200)
    fishGenerator.generate()
    fishGenerator.save()
    fishGenerator.saveC()
    fishArrayGenerator = FishArrayGenerator((1,1,1,1,1))
    fishArrayGenerator.generate()
    fishArrayGenerator.save()
    fishArrayGenerator.saveC()

#if __name__ == '__main__':
#    #鱼预生成，每种鱼生成1千条数据
#    fishGenerator = FishGenerator()
#    fishGenerator.load()
#    fishArrayGenerator = FishArrayGenerator()
#    fishArrayGenerator.load()
