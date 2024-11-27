##########################
# Author: Cornelius Marx
# Date: November 17th 2024
##########################

from .overridable_yaml_object import OverridableYamlObject
from .rule import When

class Artifacts(OverridableYamlObject):
    """
    Produced and needed by a job.
    """
    def __init__(self, paths: list[str] | None = None, when: None|When = None, lifetime: str = None, junit_report: str | None = None, yaml_override:dict | None = None):
        super().__init__(yaml_override)
        self.paths = paths
        self.lifetime = lifetime
        self.when = when
        self.junit_report = junit_report
        self.produced_by = None
        self.needed_by = []

    def to_yaml_impl(self):
        y = {}
        if self.paths is not None:
            y["paths"] = self.paths

        if self.junit_report is not None:
            if self.paths is not None:
                raise RuntimeError("paths and junit_report given")
            y["reports"] = {"junit": self.junit_report}

        if self.lifetime:
            y["expire_in"] = self.lifetime

        if self.when:
            y["when"] = str(self.when)

        return y
