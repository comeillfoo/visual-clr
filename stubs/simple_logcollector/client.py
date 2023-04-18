#!/usr/bin/env python3
from time import sleep, time
import grpc
from logcollector_pb2_grpc import LogCollectorStub
from logcollector_pb2 import SessionStartRequest, SessionFinishRequest, TimestampRequest, ResponseTypes, SessionFinishReason
from enum import Enum
import random


class States(Enum):
    PENDING = 0
    WORKING = 1


def test(pid: int, collector: LogCollectorStub) -> ResponseTypes:
    CLASS_NAME = 'System.String'
    ret = collector.ClassLoadStartStamp(TimestampRequest(pid=pid, time=time(), payload=CLASS_NAME))
    print('FMS: ClassLoadStart stamped', ret)
    if not ret.is_ok:
        return ret.response_type
    sleep(random.randint(0, 20) / 10)
    ret = collector.ClassLoadFinishedStamp(TimestampRequest(pid=pid, time=time(), payload=CLASS_NAME))
    print('FMS: ClassLoadFinish stamped', ret)
    if not ret.is_ok:
        return ret.response_type
    sleep(random.randint(0, 20) / 10)
    ret = collector.ClassUnloadStartStamp(TimestampRequest(pid=pid, time=time(), payload=CLASS_NAME))
    print('FMS: ClassUnloadStart stamped', ret)
    if not ret.is_ok:
        return ret.response_type
    sleep(random.randint(0, 20) / 10)
    ret = collector.ClassUnloadFinishedStamp(TimestampRequest(pid=pid, time=time(), payload=CLASS_NAME))
    print('FMS: ClassUnloadFinish stamped', ret)
    return ret.response_type


PID = 16054
COLLECTOR_PORT = 50051
STATE = States.PENDING

channel = grpc.insecure_channel(f'localhost:{COLLECTOR_PORT}')
collector = LogCollectorStub(channel)
print('FMS: started')
while True:
    if STATE == States.PENDING:
        print('FMS: trying to start a new session')
        if collector.StartSession(SessionStartRequest(pid=PID)).is_ok:
            STATE = States.WORKING
            print('FMS: a new session started')
        else:
            print('FMS: can\'t start a new session')
    elif STATE == States.WORKING:
        print('FMS: sending the payload')
        if test(PID, collector) != ResponseTypes.OK:
            print('FMS: errors while sending requests. Trying reconnect')
            STATE = States.PENDING
print('FMS: finished')
