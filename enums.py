import enum


class ThreadStates(str, enum.Enum):
    CREATED='created'
    DESTROYED='destroyed'
    RESUMED='resumed'
    SUSPENDED='suspended'


class GcGenerations(enum.Enum):
    GEN0 = 0
    GEN1 = 1
    GEN2 = 2
    LARGE_OBJECT_HEAP = 3
    PINNED_OBJECT_HEAP = 4
    UNDEFINED = 5

    @classmethod
    def from_value(cls, value: int):
        try:
            return GcGenerations(value)
        except:
            return GcGenerations.UNDEFINED