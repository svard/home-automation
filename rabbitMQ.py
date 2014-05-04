#!/usr/bin/python
# coding=utf-8
'''
Created on 2 may 2014

@author: Kristofer Svärd
'''

import pika

def publish(routingKey, data, host="192.168.0.108"):
    connection = pika.BlockingConnection(pika.ConnectionParameters(host=host))
    channel = connection.channel()

    channel.exchange_declare(exchange='automation', type='direct')
    channel.basic_publish(exchange='automation', routing_key=routingKey, body=data)
    connection.close()
