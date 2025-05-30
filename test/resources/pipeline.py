#!/usr/bin/env python3

from spycilab import *
import time
import subprocess

stages = StageStore()
stages.test = Stage("Testing")

variables = VariableStore()
variables.test_variable = Variable(default_value="my_default", description="This is a test variable.")

jobs = JobStore()

jobs.test = Job("Unit Tests", JobConfig(stage=stages.test, work=lambda: print(f"testing stuff (var='{variables.test_variable}')...") or True,
                                        rules=[Rule(variables.test_variable.equal_to("A") | variables.test_variable.equal_to("B"),
                                                    when=When.always)]))

jobs.fail = Job("Always Fails", JobConfig(stage=stages.test, work=lambda: print("fail") or False))

jobs.prefix = Job("Prefix Job", JobConfig(stage=stages.test, rules=[Rule(when=When.never)], run_prefix="echo $test_variable && time --portability", work=lambda: time.sleep(1) or True))

jobs.subprocess = Job("Subprocess Job", JobConfig(stage=stages.test,
                                                  work=lambda: subprocess.run(f"echo \"from subprocess: ${variables.test_variable.name}\"", shell=True).returncode == 0,
                                                  rules=[Rule(when=When.never)]
                                                ))

workflow = [
    Rule(variables.CI_COMMIT_BRANCH.equal_to("master")),
    Rule(variables.CI_COMMIT_TAG.full_match("skip-.*"), when=When.never)
]

if __name__ == "__main__":
    Pipeline(stages=stages, jobs=jobs, variables=variables, workflow=workflow).main()
