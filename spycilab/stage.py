##########################
# Author: Cornelius Marx
# Date: November 17th 2024
##########################

from .typed_store import TypedStore

class Stage:
    def __init__(self, name:str):
        self.name = name

    def to_yaml(self):
        return self.name

class StageStore(TypedStore[Stage]):
    def to_yaml(self):
        s = []
        for k, v in self.__dict__.items():
            if isinstance(v, Stage):
                s.append(v.name)
            else:
                raise ValueError(f"StageStore member '{k}' is not of type Stage")
        return s

    def all_names(self):
        return [ s.name for s in self.all() ]
