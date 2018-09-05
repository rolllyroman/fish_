#!/usr/bin/env python
# -*- coding:utf-8 -*-

"""
Author: $Author$
Date: $Date$
Revision: $Revision$

Description: Describe module function
"""
import sys
import subprocess

BASE_PORT = 10531

IP = 'a2.dongshenggame.cn'
NAME = 'ds_pickfish_%s'
code = 'CNY'

gameServerCounts = {
    5000       :       2,
    5001       :       2,
    5002       :       2,
}

for gameId, count in gameServerCounts.iteritems():
    for i in xrange(count):
        subprocess.Popen('python -m run_server -i %s -p %s -c %s -n %s -g %s'%(IP, BASE_PORT, code, NAME%gameId, gameId), shell=True)
        BASE_PORT += 1
