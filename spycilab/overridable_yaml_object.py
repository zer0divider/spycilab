##########################
# Author: Cornelius Marx
# Date: November 17th 2024
##########################

import typing

class OverridableYamlObject:
    def __init__(self, yaml_override:dict | None = None):
        self.yaml_override = yaml_override

    def to_yaml_impl(self):
        raise NotImplementedError("this function should be implemented by subclass")

    @typing.final
    def to_yaml(self):
        y = self.to_yaml_impl()
        if self.yaml_override is not None:
            for k in self.yaml_override.keys():
                y[k] = self.yaml_override[k]

        return y
