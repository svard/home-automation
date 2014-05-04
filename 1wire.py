#!/usr/bin/python
# coding=utf-8
'''
Created on 1 may 2014

@author: Kristofer Svärd
'''
import sys
import os
import logging
import redis
import urllib2
import json
import argparse
import time
import rabbitMQ

logging.basicConfig(format='%(levelname)s:%(asctime)s %(message)s', datefmt='%Y-%m-%d %H:%M:%S', filename='/home/kristofer/logs/light.log', level=logging.INFO)
parser = argparse.ArgumentParser()

def readLightValue():
    f = open("/mnt/1wire/20.1BFB0C000000/volt.B", "r")
    lightVal = float(f.read().strip())
    logging.debug("Read light value %f", lightVal)

    return lightVal

def readTemperatureValue():
    f = open("/mnt/1wire/28.294683050000/temperature", "r")
    tempVal = float(f.read().strip())
    logging.debug("Read temp value %f", tempVal)

    return round(tempVal, 1)

def getLightState(host, id):
    url = host + "/api/light/" + str(id)
    logging.debug("Querying %s", url)

    request = urllib2.Request(url)
    response = urllib2.urlopen(request)
    light = json.loads(response.read().decode())
    logging.debug("Decoded response %s", light)

    return light['state']

def getThresholdCount():
    redisServer = redis.Redis("localhost")
    count = redisServer.get("thresholdcount")
    logging.debug("Threshold count %d", int(count))

    return int(count)

def incrementThresholdCount():
    redisServer = redis.Redis("localhost")

    logging.debug("Incrementing thresholdcount")
    redisServer.incr("thresholdcount")

def resetThresholdCount():
    redisServer = redis.Redis("localhost")

    logging.debug("Reset thresholdcount")
    redisServer.set("thresholdcount", 0)

def getUTCTimeString():
    return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())

def getLocalTimeString():
    return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())

def publishTemperature():
    temp = readTemperatureValue()
    utcTime = getUTCTimeString()
    localTime = getLocalTimeString()
    data = json.dumps({"deviceId": 100, "deviceName": "Indoor", "temperature": temp, "date": utcTime, "dateStr": localTime})

    rabbitMQ.publish("temps", data)

def turnOnLight(host, id):
    currState = getLightState(host, id)
    currHour = int(time.strftime("%H", time.localtime()))

    if currState == "OFF" and currHour > 12 and currHour < 23:
        logging.info("Turning on light: %d", id)
        url = host + "/api/light/" + str(id)
        data = json.dumps({"state": "ON"})
        request = urllib2.Request(url, data.encode('utf-8'), {"Content-Type": "application/json"})
        request.get_method = lambda: 'PUT'
        response = urllib2.urlopen(request)

parser.add_argument("host", help="light controlling host", action="store")
parser.add_argument("threshold", help="threshold level for turning on lights", action="store", type=float)
#parser.add_argument("-p", "--publish", help="publish to message bus", action="store_true", dest="publish")
args = parser.parse_args()

if readLightValue() < args.threshold:
    incrementThresholdCount()
    if getThresholdCount() > 3:
        turnOnLight(args.host, 2)
        turnOnLight(args.host, 3)
        turnOnLight(args.host, 4)
        turnOnLight(args.host, 5)
        resetThresholdCount()

publishTemperature()
