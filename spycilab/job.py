##########################
# Author: Cornelius Marx
# Date: November 17th 2024
##########################

from __future__ import annotations

import typing

from .overridable_yaml_object import OverridableYamlObject
from .typed_store import TypedStore
from .artifact import Artifacts
from .rule import Rule, When
from .stage import Stage


class JobConfig:
    """
    Configuration for a job.
    Job configs are put in separate class to allow for easier extension.
    """

    def __init__(self, stage: Stage = None,
                 work: typing.Callable | None = None,
                 rules: None | list[Rule] | Rule = None,
                 artifacts: None | Artifacts = None,
                 needs: None | list[Artifacts] | Artifacts = None,
                 depends: None | list[Job] | Job = None,
                 tags: None | list[str] | str = None,
                 run_prefix: str | None = None,
                 extends: list[JobConfig] | JobConfig | None = None,
                 when: When | None = None,
                 allow_failure: bool | None = None,
                 yaml_override: dict | None = None):
        """
        :param stage: in which stage should the job appear
        :param work: what should the job do. must be a callable object
        """

        def make_list(value) -> list | None:
            if isinstance(value, list):
                return value
            elif value is None:
                return None
            else:
                return [value]

        self.stage = stage
        self.work = work
        self.rules = make_list(rules)
        self.artifacts = artifacts
        self.needs = make_list(needs)
        self.tags = make_list(tags)
        self.depends = make_list(depends)
        self.run_prefix = run_prefix
        self.when = when
        self.allow_failure = allow_failure
        self.yaml_override = yaml_override

        if extends:
            extends = make_list(extends)
            for k, v in self.__dict__.items():
                if k == "yaml_override":
                    # special handling for yaml_override
                    # merge together all dictionaries
                    # self.yaml_override has the highest priority,
                    # extends[0].yaml_override has lowest

                    # get all possible keys
                    override_keys = []
                    for e in extends:
                        if e.yaml_override is not None:
                            override_keys.extend(e.yaml_override.keys())

                    # merge dictionaries
                    for override_k in override_keys:
                        if self.yaml_override.get(override_k) is None:
                            extends_v = None
                            for e in extends:
                                override_v = e.yaml_override.get(override_k)
                                if override_v is not None:
                                    extends_v = override_v
                            if extends_v is not None:
                                self.yaml_override[override_k] = extends_v
                elif v is None:
                    # set config from extended JobConfig(s)
                    # self has the highest priority,
                    # extends[0] has lowest
                    extend_v = None
                    for e in extends:
                        if e.__dict__[k] is not None:
                            extend_v = e.__dict__[k]

                    self.__dict__[k] = extend_v

    def copy(self) -> JobConfig:
        j = JobConfig()
        j.stage = self.stage
        j.work = self.work
        j.rules = self.rules.copy()
        j.artifacts = self.artifacts
        j.needs = self.needs.copy()
        j.tags = self.tags.copy()
        j.depends = self.depends.copy()
        j.run_prefix = self.run_prefix
        j.when = self.when
        j.allow_failure = self.allow_failure
        j.yaml_override = self.yaml_override.copy()
        return j

class Job(OverridableYamlObject):
    """
    This class represents a pipeline job.
    """

    def __init__(self, name: str, config: JobConfig = JobConfig()):
        """
        :param name: the name of the job as it will be displayed in the pipeline
        """
        super().__init__(config.yaml_override)
        self.internal_name = None
        self.name = name
        self.config = config

        # check deps and needs
        if self.config.needs is not None and self.config.depends is not None:
            raise RuntimeError(f"'needs' and 'depends' specified for job '{name}'")

        # check artifacts
        if self.config.artifacts is not None:
            if self.config.artifacts.produced_by is None:
                self.config.artifacts.produced_by = self
            else:
                raise RuntimeError(
                    f"Artifact '{self.config.artifacts.paths}' already produced by job '{self.config.artifacts.produced_by.name}'")

        # append this job to artifact needed list
        if self.config.needs is not None:
            for n in self.config.needs:
                n.needed_by.append(self)
                if n.produced_by is None:
                    raise RuntimeError(f"Artifact '{self.config.artifacts.paths}' is not produced by any job")

    def __gt__(self, other) -> bool:
        return self.name > other.name

    def run(self):
        if self.config.work is not None:
            self.config.work()
        else:
            print("Nothing to do.")

    def to_yaml_impl(self):
        if self.internal_name is None:
            raise RuntimeError(f"Job '{self.name}' has no internal name.")

        if self.config.stage is None:
            raise RuntimeError(f"Job '{self.name}' has no stage.")

        y = {
            "stage": self.config.stage.name,
            "extends": ".job_base",
            "variables": {
                "INTERNAL_JOB_NAME": self.internal_name
            }
        }
        if self.config.run_prefix is not None:
            y["variables"]["JOB_RUN_PREFIX"] = self.config.run_prefix
        if self.config.rules is not None:
            y["rules"] = [r.to_yaml() for r in self.config.rules]
        if self.config.artifacts is not None:
            y["artifacts"] = self.config.artifacts.to_yaml()
        if self.config.needs is not None:
            y["needs"] = [n.produced_by.name for n in self.config.needs]
        if self.config.depends is not None:
            y["dependencies"] = [n.name for n in self.config.depends]
            # TODO: warn when job has other rules than dependend job
        if self.config.tags is not None:
            y["tags"] = self.config.tags
        if self.config.when is not None:
            y["when"] = str(self.config.when)
        if self.config.allow_failure is not None:
            y["allow_failure"] = str(self.config.allow_failure)

        return y


class JobStore(TypedStore[Job]):
    def update_jobs(self):
        """
        Make sure jobs know their own name
        :return:
        """
        for k, v in self.__dict__.items():
            v.internal_name = k


def job_work(job:Job):
    def decorator(func:typing.Callable):
        job.config.work = func
        return func

    return decorator