#!/usr/bin/env python3
from threading import Lock

class SafeSet(set):
    def __init__(self, *args, **kwargs):
        self._lock = Lock()
        super(SafeSet, self).__init__(*args, **kwargs)

    def add(self, elem):
        self._lock.acquire()
        try:
            super(SafeSet, self).add(elem)
        finally:
            self._lock.release()

    def remove(self, elem):
        self._lock.acquire()
        try:
            super(SafeSet, self).remove(elem)
        finally:
            self._lock.release()

    def clone(self) -> set:
        self._lock.acquire()
        result = None
        try:
            result = self.copy()
        except:
            result = None
        finally:
            self._lock.release()
        return result
