# -*- coding:utf-8 -*-
#!/bin/python

"""
Author: Pipo
Date: $Date$
Revision: $Revision$

Description: Redis
"""
import redis

redisdb = None

def getInst(dbNum):
    global redisdb
    redisdb = redis.ConnectionPool(host="127.0.0.1", port=6379, db=dbNum, password='Fkkg65NbRwQOnq01OGMPy5ZREsNUeURm')
    return redis.Redis(connection_pool=redisdb)
