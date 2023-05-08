import enum


class ThreadStates(str, enum.Enum):
    CREATED='created'
    DESTROYED='destroyed'
    RESUMED='resumed'
    SUSPENDED='suspended'
