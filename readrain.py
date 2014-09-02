#!/usr/bin/python
# coding=utf-8
'''
Created on 11 june 2014

@author: Kristofer Svärd
'''
import json
import re
import subprocess
import sys
import logging
import redis
import time
import rabbitMQ
from optparse import OptionParser

logging.basicConfig(format='%(levelname)s:%(asctime)s %(message)s', datefmt='%Y-%m-%d %H:%M:%S', filename='/home/kristofer/logs/readrain.log', level=logging.DEBUG)

def getUTCTimeString():
    return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())

def getTotalRainLevel():
    redisServer = redis.Redis("localhost")
    total = redisServer.get("raintotal")

    if total:
        logging.debug("Stored rain total: %d", float(total))
        return float(total)
    else:
        logging.debug("No stored rain total")
        return total

def setTotalRainLevel(raintotal):
    redisServer = redis.Redis("localhost")
    redisServer.set("raintotal", raintotal)

def getRainRate(currentRainTotal):
    rainTotal = getTotalRainLevel()

    setTotalRainLevel(currentRainTotal)

    if rainTotal and rainTotal > currentRainTotal:
        return 0.0
    elif rainTotal:
        return round((currentRainTotal - rainTotal), 1)
    else:
        return 0.0

def readRainLevel(id):
    rainDict = {}
    rawReponse = subprocess.Popen(["tdtool", "--list-sensors"], stdout=subprocess.PIPE).stdout.read()
    lines = rawReponse.split("\n")
    for line in lines:
        m = re.match("\S+=(?P<type>\S+)\t\S+=(?P<protocol>\S+)\t\S+=(?P<model>\S+)\t\S+=(?P<id>\d+)\t\S+=(?P<rainrate>\d+.\d+)\t\S+=(?P<raintotal>\d+.\d+)", line)
        if m:
            if int(m.group("id")) == id:
                rainDict["id"] = int(m.group("id"))
                rainDict["rainrate"] = getRainRate(float(m.group("raintotal")))
                rainDict["date"] = getUTCTimeString()

    return rainDict

def publishRainLevel(rain, name, host):
    data = json.dumps({"deviceId": rain["id"], "deviceName": name, "rainrate": rain["rainrate"], "date": rain["date"]})

    rabbitMQ.publish("rain", data, host)

if __name__ == '__main__':
    parser = OptionParser()
    parser.add_option("-o", "--host", dest="host",
                  help="host to send rain reading to", metavar="HOST", action="store", type="string")
    parser.add_option("-n", "--name", dest="name",
                  help="name of this rain sensor", metavar="NAME", action="store", type="string")
    parser.add_option("-i", "--id", dest="id",
                  help="device id to read", metavar="ID", action="store", type="int")

    (options, args) = parser.parse_args()

    if(options.host == None):
        parser.error("Host is missing")
    else:
        host = options.host
    if(options.name == None):
        parser.error("Name is missing")
    else:
        deviceName = options.name
    if(options.id == None):
        parser.error("Id is missing")
    else:
        id = options.id

    result = readRainLevel(id)
    publishRainLevel(result, deviceName, host)

    sys.exit(0)
