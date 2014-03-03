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
import sys
import logging
import MySQLdb as mysql
import pika
from datetime import datetime
from optparse import OptionParser

logging.basicConfig(format='%(levelname)s:%(asctime)s %(message)s', datefmt='%Y-%m-%d %H:%M:%S', filename='/home/kristofer/logs/readtemp.log', level=logging.DEBUG)

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
        if __haveBuffer():
            sendBuffer(host)
    except urllib2.URLError, e:
        logging.error("Failed to send measurement.")
        bufferTemperature(temp, name)
    else:
        f.close()
#        logging.info("Reported a temp. of " + str(temp["temp"]) + " degrees at " + temp["date"])

def publishTemperature(temp, name, host):
    data = json.dumps({"deviceId": temp["id"], "deviceName": name, "temperature": temp["temp"], "date": temp["unixdate"], "dateStr": temp["date"]})

    connection = pika.BlockingConnection(pika.ConnectionParameters(host=host))
    channel = connection.channel()

    channel.exchange_declare(exchange='automation', type='direct')
    channel.basic_publish(exchange='automation', routing_key='temps', body=data)
    connection.close()

def bufferTemperature(temp, name):
    dbConn = __connectDb()

    try:
        cursor = dbConn.cursor()
        logging.debug("INSERT INTO tempbuffer(device_id, device_name, temperature, date, date_str) VALUES(%d, '%s', %.1f, %d, '%s')" % (temp["id"], name, temp["temp"], temp["unixdate"], temp["date"]))
        cursor.execute("INSERT INTO tempbuffer(device_id, device_name, temperature, date, date_str) VALUES(%d, '%s', %.1f, %d, '%s')" % (temp["id"], name, temp["temp"], temp["unixdate"], temp["date"]))
        dbConn.commit()
    except mysql.Error, e:
        logging.error("Error buffering to db %d: %s" % (e.args[0],e.args[1]))
        dbConn.rollback()
        sys.exit(1)
    finally:
        if dbConn:
            dbConn.close()

def sendBuffer(host):
    dbConn = __connectDb()

    try:
        cursor = dbConn.cursor(mysql.cursors.DictCursor)
        cursor.execute("SELECT * FROM tempbuffer")

        rows = cursor.fetchall()
        for row in rows:
            data = json.dumps({"deviceId": row["device_id"], "deviceName": row["device_name"], "temperature": row["temperature"], "date": row["date"], "dateStr": row["date_str"]})
            try:
                post = urllib2.Request(host, data, {"Content-Type": "application/json"})
                f = urllib2.urlopen(post)
            except urllib2.URLError, e:
                logging.error("Failed to send measurement.")
            finally:
                logging.debug("Reported a temp. of " + str(row["temperature"]) + " degrees at " + row["date_str"])
                logging.debug("DELETE FROM tempbuffer WHERE buffer_id=%d" % row["buffer_id"])
                cursor.execute("DELETE FROM tempbuffer WHERE buffer_id=%d" % row["buffer_id"])
                dbConn.commit()
    except mysql.Error, e:
        logging.error("Error reading from db %d: %s" % (e.args[0],e.args[1]))
        sys.exit(1)
    finally:
        dbConn.close()
        f.close()

def __connectDb():
    dbConn = None

    try:
        dbConn = mysql.connect('192.168.0.192', 'kristofer', 'gu7101L2', 'automation')

    except mysql.Error, e:
        logging.error("Failed to connect to db %d: %s" % (e.args[0],e.args[1]))
        sys.exit(1)

    return dbConn

def __haveBuffer():
    dbConn = __connectDb()

    try:
        cursor = dbConn.cursor()

        cursor.execute("SELECT * FROM tempbuffer")

        if int(cursor.rowcount) > 0:
            logging.debug("%d buffered temperatures exists." % int(cursor.rowcount))
            return True
        else:
#            logging.debug("No buffered temperatures exists.")
            return False

    except mysql.Error, e:
        logging.error("Error reading db %d: %s" % (e.args[0],e.args[1]))
        sys.exit(1)

    finally:
        if dbConn:
            dbConn.close()


if __name__ == '__main__':
    parser = OptionParser()
    parser.add_option("-o", "--host", dest="host",
                  help="host to send temperature reading to", metavar="HOST", action="store", type="string")
    parser.add_option("-n", "--name", dest="name",
                  help="name of this temperature sensor", metavar="NAME", action="store", type="string")
    parser.add_option("-i", "--id", dest="id",
                  help="device id to read", metavar="ID", action="store", type="int")
    parser.add_option("-p", "--publish", dest="pub",
                  help="publish to message bus", action="store_true")
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
    if(options.pub):
        publishTemperature(result, deviceName, host)
    else:
        reportTemperature(result, deviceName, host)

#     result = readTemperature(deviceId)
#     reportTemperature(result, deviceName, host)

    sys.exit(0)
