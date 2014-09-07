#!/usr/bin/python
# coding=utf-8
'''
Created on 15 mar 2013

@author: Kristofer Svärd
'''
import subprocess
import re
import argparse
import redis
import string
import sys
import urllib2
import json

def switchLight(state, id):
    url = "http://tomcat.kristofersvard.se/services/api/light/" + str(id)
    data = json.dumps({"state": state})
    request = urllib2.Request(url, data.encode('utf-8'), {"Content-Type": "application/json"})
    request.get_method = lambda: 'PUT'
    response = urllib2.urlopen(request)

def initLight():
    redisServer = redis.Redis("192.168.0.108")
    response = subprocess.Popen(["tdtool", "--list"], stdout=subprocess.PIPE).stdout.read()
    lines = response.split("\n")
    for line in lines:
        m = re.match("(?P<id>\d+)\s+(?P<name>\S+)\s+(?P<state>\S+)", line)
        if m:
            redisServer.hmset("light:%s" % m.group("id"), {"id": m.group("id"), "name": m.group("name"), "state": m.group("state")})


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--on", dest="on", metavar="ID", default=None, help="light on")
    group.add_argument("--off", dest="off", metavar="ID", default=None, help="light off")
    group.add_argument("--init", dest="init", default=False, action="store_true", help="initialise the redis store")
    args = parser.parse_args()

    if args.on:
        switchLight("ON", args.on)
    elif args.off:
        switchLight("OFF", args.off)
    elif args.init:
        initLight()

    sys.exit(0)
