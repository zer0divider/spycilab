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

