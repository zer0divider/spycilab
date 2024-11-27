##########################
# Author: Cornelius Marx
# Date: November 17th 2024
##########################

import typing

GenericStoreT = typing.TypeVar('GenericStoreT')

class TypedStore(typing.Generic[GenericStoreT]):
    """
    Dictionary for a given type.
    New values are to be added through: my_store.new_val = ...
    """
    def add(self, identifier:str, s:GenericStoreT) -> GenericStoreT:
        self.__dict__[identifier] = s
        return s

    def all(self):
        return self.__dict__.values()

    def all_identifier(self):
        return self.__dict__.keys()

    def get(self, internal_name:str):
        return self.__dict__.get(internal_name)
