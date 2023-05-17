#!/usr/bin/env python3
from collections import namedtuple
from datetime import datetime

def unix2str(timestamp: float) -> str:
    return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S.%f')

SessionQueues = namedtuple('SessionQueues', ['pending', 'start', 'finish', 'logs', 'threads', 'stats', 'allocations', 'objects'])

class ManagedObject:
    def __init__(self, class_name, size, generation, is_retained):
        self.class_name = class_name
        self.size = size
        self.generation = generation
        self.is_retained = is_retained

# ManagedObject = namedtuple('ManagedObject', ['class_name', 'size', 'generation', 'is_retained'])
