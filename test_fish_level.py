from common.data.fish_levels import *
from common.logic.global_control import GlobalControl
import math

totalRate = 1
maxCountOfFishs = 4

level2fishs = dict([(i, []) for i in xrange(len(FISH_LEVELS_DATA))])
print(level2fishs)