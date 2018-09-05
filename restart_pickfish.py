import subprocess
import multiprocessing
from subprocess import PIPE
import os
from common.common_db_define import *
from common.db_utils import sendProtocol2GameService
import redis_instance
import time
import sys

def execute(script, shell=True, result=True):
    if result:
        p = subprocess.Popen(script, shell=shell,
                             stdout=PIPE, stdin=PIPE, stderr=PIPE)
        return p.communicate()
    else:
        p = subprocess.Popen(script, shell=shell)
    return p

def checkProcess(name):

    refShell='ps -aux | grep -v "grep" | grep -v "%s" | grep %s | wc -l' % (sys.argv[0], name)
    # print(refShell)
    result, error = execute(refShell)
    print('execResult:%s' % result)
    #if not error:
    code = int(result)
    return code
    #raise error


def restart(gameid, name, ip):

    redis = redis_instance.getInst(1)
    sendProtocol2GameService(redis, gameid, HEAD_SERVICE_PROTOCOL_GAME_CLOSE, ip)
    print("start close gameid %s name %s" % (gameid, name))
    while True:
        code = checkProcess(name)
        if code == 0:
            break
        time.sleep(3)
        print("restart %s... %s ... %s" % (gameid, name, code))
    print("Success")
    #result, error = execute("python run_servers.py")

if __name__ == "__main__":

    BASE_PORT = 12345
    IP = '192.168.16.50'
    NAME = 'ds_pickfish_%s'
    code = 'CNY'
    gameServerCounts = {
        5000: 1,
        5001: 1,
        5002: 1,
    }
    execute("svn update")
    for gameId, count in gameServerCounts.iteritems():
        for i in xrange(count):
            restart(gameId, NAME % gameId, IP)
            subprocess.Popen('python -m run_server -i %s -p %s -c %s -n %s -g %s'%(IP, BASE_PORT, code, NAME%gameId, gameId), shell=True)
            BASE_PORT += 1
    #result, error = execute("python -m run_servers.py")
