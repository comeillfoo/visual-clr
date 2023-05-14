#!/usr/bin/env python3
from collections import namedtuple
from datetime import datetime

def unix2str(timestamp: float) -> str:
    return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S.%f')

SessionQueues = namedtuple('SessionQueues', ['pending', 'start', 'finish', 'logs', 'threads', 'stats', 'allocations', 'objects'])

ManagedObject = namedtuple('ManagedObject', ['class_name', 'size', 'generation', 'created', 'disposed'])
