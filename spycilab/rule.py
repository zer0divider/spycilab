from __future__ import annotations

from .overridable_yaml_object import OverridableYamlObject

from .variable import Condition
from .enum_string import EnumString

class When(EnumString):
    always = "always"
    never = "never"
    manual = "manual"
    on_success = "on_success"
    on_failure = "on_failure"

class Rule(OverridableYamlObject):
    """
    This class bundles a Condition with a 'when' statement
    """
    def __init__(self, condition: Condition|None = None, when: When|None = None, allow_failure: bool|None = None, yaml_override: dict | None = None):
        super().__init__(yaml_override)
        self.when = when
        self.allow_failure = allow_failure
        self.condition = condition

    def eval(self):
        if self.condition is None:
            return True
        else:
            return self.condition.eval()

    @staticmethod
    def sets_equal(a:list[Rule]|None, b:list[Rule]|None) -> bool:
        """
        Check whether two rule lists generate identical yaml outputs
        :return:
        """
        if (a is None) and (b is None):
            return True
        if (a is None) != (b is None):
            return False
        if len(a) != len(b):
            return False
        for i in range(len(a)):
            if a[i] is not b[i]: # this is quicker if rules are actually the same object (common case)
                if a[i].to_yaml() != b[i].to_yaml(): # not same object, check whether generated yaml are identical
                    return False

        return True


    def to_yaml_impl(self) -> dict:
        y = {}
        if self.condition is not None:
            y["if"] = self.condition.to_yaml()
        if self.when is not None:
            y["when"] = str(self.when)
        if self.allow_failure is not None:
            y["allow_failure"] = self.allow_failure
        if not y:
            raise RuntimeError("Either a condition or 'when' has to be specified.")
        return y

