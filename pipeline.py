#!/usr/bin/env python3
from spycilab import *
from subprocess import run
import sys

stages = StageStore()
stages.test = Stage("Testing")

variables = VariableStore()

pytest_result = Artifacts(when=When.always, junit_report="pyunit.xml")

# unit tests with pytest
def run_pytest():
    r = run(["python3", "-m", "pytest", "--junitxml", pytest_result.junit_report])
    return r.returncode


jobs = JobStore()

jobs.unit_tests = Job("Unit Tests", JobConfig(stage=stages.test, work=run_pytest, artifacts=pytest_result))

jobs.z = Job("​Z", JobConfig(stage=stages.test))
jobs.y = Job("Y", JobConfig(stage=stages.test))

workflow = [
    Rule(variables.pipeline_source_is(PipelineSource.push) & variables.CI_OPEN_MERGE_REQUESTS.is_set(), when=When.never),
    Rule(when=When.always)
]

if __name__ == "__main__":
    Pipeline(stages=stages, jobs=jobs, variables=variables, workflow=workflow).main()
