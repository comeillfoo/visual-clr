#!/usr/bin/env python3
from collections import namedtuple

SessionQueues = namedtuple('SessionQueues', ['pending', 'start', 'finish', 'logs', 'threads'])