#!/usr/bin/python
# coding=utf-8
'''
Created on 14 dec 2012

@author: Kristofer Svärd
'''
import json
import re
import subprocess
import urllib2
from datetime import datetime
from optparse import OptionParser

def readTemperature(deviceId):
    tempDict = {}
    rawReponse = subprocess.Popen(["tdtool", "--list"], stdout=subprocess.PIPE).stdout.read()
    lines = rawReponse.split("\n")
    for line in lines:
        m = re.match("\S+\s+\S+\s+(?P<id>\d+)\s+(?P<temp>\S+)\s+\S+\s+(?P<date>\S+ \S+)", line)
        if m:
            if (int(m.group("id")) == deviceId):
                tempDict["id"] = int(m.group("id"))
                tempDict["temp"] = float(m.group("temp").strip("°"))
                tempDict["date"] = m.group("date")
                mydate = datetime.strptime(m.group("date"), "%Y-%m-%d %H:%M:%S")
                tempDict["unixdate"] = int(mydate.strftime("%s"))

    return tempDict

def reportTemperature(temp, name, host):
    data = json.dumps({"deviceId": temp["id"], "deviceName": name, "temperature": temp["temp"], "date": temp["unixdate"], "dateStr": temp["date"]})
    
    post = urllib2.Request(host, data, {"Content-Type": "application/json"})
    
    try:
        f = urllib2.urlopen(post)
    except urllib2.URLError, e:
        print "Failed to send measurement. Response code %d" % (e.code)
    else:
        f.close()
        print "Reported a temp. of " + str(temp["temp"]) + " degrees at " + temp["date"]

if __name__ == '__main__':
    parser = OptionParser()
    parser.add_option("-o", "--host", dest="host",
                  help="host to send temperature reading to", metavar="HOST", action="store", type="string")
    parser.add_option("-n", "--name", dest="name",
                  help="name of this temperature sensor", metavar="NAME", action="store", type="string")
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
        deviceId = options.id
    
    result = readTemperature(deviceId)
    reportTemperature(result, deviceName, host)
