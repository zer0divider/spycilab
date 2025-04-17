##########################
# Author: Cornelius Marx
# Date: November 17th 2024
##########################

from __future__ import annotations

import re
from .enum_string import EnumString
from enum import Enum

from .overridable_yaml_object import OverridableYamlObject
from .typed_store import TypedStore


class PipelineSource(EnumString):
    api = "api"
    external = "external"
    merge_request_event = "merge_request_event"
    push = "push"
    schedule = "schedule"
    trigger = "trigger"
    web = "web"


class Variable(OverridableYamlObject):
    """
    This class represents a CI/CD variable.
    """

    def __init__(self, default_value: str = "", description=None, options: None | list[str] = None,
                 yaml_override: dict | None = None, show=False):
        """
        :param default_value:
        :param description: see Gitlab-CI YAML
        :param options: see Gitlab-CI YAML
        :param yaml_override: override keys in final YAML
        :param show: if true print the value of the variable before running a job
        """
        super().__init__(yaml_override)
        self.name = None  # name is set from variable store
        self.default_value = default_value
        self.show = show
        self.value = default_value
        self.description = description
        self.options = options

        if self.options is not None and self.default_value not in self.options:
            raise ValueError(f"Variable '{self.name}': default value must be one of {self.options}")

    def check_name(self):
        if self.name is None:
            raise RuntimeError("usage of variable before name was given")

    def check_value(self):
        if self.options is not None:
            if self.value not in self.options:
                raise ValueError(f"Invalid value '{self.value}' for variable '{self.name}', valid options are {self.options}")

    def __str__(self) -> str:
        return self.value

    def __bool__(self) -> str:
        return self.value is not None and self.value != ""

    def equal_to(self, other: str | Variable) -> Condition:
        return Condition.equal(self, other)

    def not_equal_to(self, other: str | Variable) -> Condition:
        return Condition.not_equal(self, other)

    def is_empty(self):
        return Condition.is_empty(self)

    def is_not_empty(self):
        return Condition.is_not_empty(self)

    def is_set(self):
        return Condition.is_set(self)

    def full_match(self, pattern: str, examples_match: list[str] | None = None,
                   examples_not_match: list[str] | None = None):
        return Condition.full_match(self, pattern, examples_match, examples_not_match)

    def to_yaml_impl(self):
        self.check_name()
        if self.description is None and self.options is None:
            y = self.default_value
        else:
            y = {"value": self.default_value}
            if self.description is not None:
                y["description"] = self.description

            if self.options is not None:
                y["options"] = self.options

        return y

    def __eq__(self, other: str | Variable) -> bool:
        if isinstance(other, str):
            return self.value == other
        else:
            return self.value == other.value


class BoolVariable(Variable):
    """
    A specialized variable that can only be set to yes/no.
    """
    TRUE_STRING = "yes"
    FALSE_STRING = "no"

    def __init__(self, default_value: bool, description=None, show: bool = False, yaml_override: dict | None = None):
        super().__init__(default_value=self.TRUE_STRING if default_value else self.FALSE_STRING,
                         options=["yes", "no"], description=description, show=show, yaml_override=yaml_override)

    def set(self, new_value: bool):
        self.value = self.TRUE_STRING if new_value else self.FALSE_STRING

    def is_true(self) -> Condition:
        return Condition.is_true(self)

    def is_false(self) -> Condition:
        return Condition.is_false(self)

    def __bool__(self) -> bool:
        """
        :return: Current value held by this variable as boolean.
        """
        v = self.value.lower()
        if v == self.TRUE_STRING:
            return True
        elif v == self.FALSE_STRING:
            return False
        else:
            raise ValueError(f"BoolVariable '{self.name}' contains illegal value '{self.value}'")


class Condition:
    """
    This implements the 'if' pipeline statement
    """

    class Type(Enum):
        EQUAL = 0
        NOT_EQUAL = 1
        FULL_MATCH = 2
        SET = 3
        AND = 4
        OR = 5

    def __init__(self, when: str = "always"):
        self.a = None  # left operand (for boolean Condition)
        self.b = None  # right operand (for boolean Condition)
        self.v = None  # variable
        self.t = None  # type
        self.s = None  # compare string

    @staticmethod
    def equal(v: Variable, s: Variable | str) -> Condition:
        c = Condition()
        c.v = v
        c.s = s
        c.t = Condition.Type.EQUAL
        return c

    @staticmethod
    def not_equal(v: Variable, s: Variable | str) -> Condition:
        c = Condition()
        c.v = v
        c.s = s
        c.t = Condition.Type.NOT_EQUAL
        return c

    @staticmethod
    def is_empty(v: Variable) -> Condition:
        return Condition.equal(v, "")

    @staticmethod
    def is_not_empty(v: Variable) -> Condition:
        return Condition.not_equal(v, "")

    @staticmethod
    def is_set(v: Variable) -> Condition:
        c = Condition()
        c.v = v
        c.t = Condition.Type.SET
        return c

    @staticmethod
    def is_true(v: BoolVariable) -> Condition:
        return Condition.equal(v, BoolVariable.TRUE_STRING)

    @staticmethod
    def is_false(v: BoolVariable) -> Condition:
        return Condition.not_equal(v, BoolVariable.TRUE_STRING)

    @staticmethod
    def full_match(v: Variable, pattern: str, examples_match: None | list[str] = None,
                   examples_not_match: None | list[str] = None) -> Condition:
        c = Condition()
        c.v = v
        c.s = pattern
        c.t = Condition.Type.FULL_MATCH
        if examples_match is not None or examples_not_match is not None:
            compiled_pattern = re.compile(pattern)
            if examples_match:
                for e in examples_match:
                    if not re.fullmatch(compiled_pattern, e):
                        raise RuntimeError(f"Pattern '{pattern}' does not match with '{e}'")

            if examples_not_match:
                for e in examples_not_match:
                    if re.fullmatch(compiled_pattern, e):
                        raise RuntimeError(f"Pattern '{pattern}' does match with '{e}'")
        return c

    @staticmethod
    def b_and(a, b) -> Condition:
        c = Condition()
        c.a = a
        c.b = b
        c.t = Condition.Type.AND
        return c

    def __and__(self, other) -> Condition:
        return Condition.b_and(self, other)

    @staticmethod
    def b_or(a, b) -> Condition:
        c = Condition()
        c.a = a
        c.b = b
        c.t = Condition.Type.OR
        return c

    def __or__(self, other) -> Condition:
        return Condition.b_or(self, other)

    def eval(self) -> bool:
        if self.t is None:
            raise RuntimeError("Type not set")
        match self.t:
            case self.Type.EQUAL:
                if isinstance(self.s, Variable):
                    return self.v.value == self.s.value
                else:
                    return self.v.value == self.s
            case self.Type.NOT_EQUAL:
                if isinstance(self.s, Variable):
                    return self.v.value != self.s.value
                else:
                    return self.v.value != self.s
            case self.Type.SET:
                return bool(self.v.value)
            case self.Type.FULL_MATCH:
                return re.fullmatch(self.s, self.v.value) is not None
            case self.Type.AND:
                return self.a.eval() and self.b.eval()
            case self.Type.OR:
                return self.a.eval() or self.b.eval()
            case _:
                raise RuntimeError("Invalid type")

    def __bool__(self) -> bool:
        return self.eval()

    def to_yaml(self) -> str:
        if self.t is None:
            raise RuntimeError("Type not set")
        match self.t:
            case self.Type.EQUAL:
                self.v.check_name()
                if isinstance(self.s, Variable):
                    return f"(${self.v.name} == ${self.s.name})"
                else:
                    return f"(${self.v.name} == '{self.s}')"
            case self.Type.NOT_EQUAL:
                self.v.check_name()
                if isinstance(self.s, Variable):
                    return f"(${self.v.name} != ${self.s.name})"
                else:
                    return f"(${self.v.name} != '{self.s}')"
            case self.Type.SET:
                self.v.check_name()
                return f"(${self.v.name})"
            case self.Type.FULL_MATCH:
                self.v.check_name()
                return f"(${self.v.name} =~ /^{self.s}$/)"
            case self.Type.AND:
                return f"({self.a.to_yaml()} && {self.b.to_yaml()})"
            case self.Type.OR:
                return f"({self.a.to_yaml()} || {self.b.to_yaml()})"
            case _:
                raise RuntimeError("Invalid type")


class VariableStore(TypedStore):
    """
    This class provides access to Variables.
    """
    # builtins from https://docs.gitlab.com/ee/ci/variables/predefined_variables.html
    # NOTE: this list is incomplete
    BUILTINS = [
        "CI_DEFAULT_BRANCH",
        "CI_PIPELINE_SOURCE",
        "CI_PIPELINE_TRIGGERED",
        "CI_PIPELINE_URL",
        "CI_REGISTRY",
        "CI_REGISTRY_IMAGE",
        "CI_REGISTRY_PASSWORD",
        "CI_REGISTRY_USER",
        "CI_REPOSITORY_URL",
        "CI_MERGE_REQUEST_ID",
        "CI_OPEN_MERGE_REQUESTS",
        "CI_COMMIT_AUTHOR",
        "CI_COMMIT_BRANCH",
        "CI_COMMIT_DESCRIPTION",
        "CI_COMMIT_MESSAGE",
        "CI_COMMIT_REF_NAME",
        "CI_COMMIT_SHA",
        "CI_COMMIT_TAG",
        "CI_JOB_NAME",
        "CI_JOB_TOKEN"
    ]

    def __init__(self):
        self.CI_DEFAULT_BRANCH = Variable("main")
        self.CI_PIPELINE_SOURCE = Variable()
        self.CI_PIPELINE_TRIGGERED = Variable()
        self.CI_PIPELINE_URL = Variable()
        self.CI_REGISTRY = Variable()
        self.CI_REGISTRY_IMAGE = Variable()
        self.CI_REGISTRY_PASSWORD = Variable()
        self.CI_REGISTRY_USER = Variable()
        self.CI_REPOSITORY_URL = Variable()
        self.CI_MERGE_REQUEST_ID = Variable()
        self.CI_OPEN_MERGE_REQUESTS = Variable()
        self.CI_COMMIT_AUTHOR = Variable()
        self.CI_COMMIT_BRANCH = Variable()
        self.CI_COMMIT_DESCRIPTION = Variable()
        self.CI_COMMIT_MESSAGE = Variable()
        self.CI_COMMIT_REF_NAME = Variable()
        self.CI_COMMIT_SHA = Variable()
        self.CI_COMMIT_TAG = Variable()
        self.CI_JOB_NAME = Variable()
        self.CI_JOB_TOKEN = Variable()

    def pipeline_source_is(self, s: PipelineSource) -> Condition:
        return self.CI_PIPELINE_SOURCE.equal_to(s.value)

    def branch_is_default(self) -> Condition:
        return Condition.equal(self.CI_COMMIT_BRANCH, self.CI_DEFAULT_BRANCH)

    def is_merge_request(self) -> Condition:
        return self.pipeline_source_is(PipelineSource.merge_request_event)

    def is_tag(self) -> Condition:
        return self.CI_COMMIT_TAG.is_set()

    def is_branch(self) -> Condition:
        return self.CI_COMMIT_BRANCH.is_set()

    def update_variable_names(self):
        """
        Make sure variables know their own name.
        Supposed to be called by pipeline object, after all variables have been added.
        :return:
        """
        for k, v in self.__dict__.items():
            v.name = k

    def check_all(self):
        for v in self.__dict__.values():
            v.check_value()

    def to_yaml(self):
        vs = {}
        for k, v in self.__dict__.items():
            if isinstance(v, Variable):
                # check name
                if k != v.name:
                    raise ValueError(f"Variable has internal name '{k}' but attribute .name is '{v.name}'.")

                if k not in VariableStore.BUILTINS:
                    vs[v.name] = v.to_yaml()
            else:
                raise ValueError(f"VariableStore member '{k}' is not of type Variable")
        return vs
