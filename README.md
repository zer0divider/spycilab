# spycilab
No, this is not a typo. The *Simple Python CI Lab* (spycilab) is a GitLab-CI YAML generator that lets you specify your CI pipeline through Python.
Here is a small example `pipeline.py`:
```python
#!/usr/bin/env python3
from spycilab import *

# create stages
S = StageStore()
S.build = Stage("Building Stuff")
S.test = Stage("Testing Stuff")

# create jobs
J = JobStore()

def work_build_app():
    print("building my app...")
    return True
    
def work_test_app():
    print("testing my app...")
    return True
    
J.build_app = Job("Build My App", JobConfig(stage=S.build, work=work_build_app))
J.test_app = Job("Test My App", JobConfig(stage=S.test, work=work_test_app))

# main
if __name__ == "__main__":
    Pipeline(jobs=J, stages=S).main()
```
When this script runs it will generate a pipeline (`.gitlab-ci.yml`) with two stages each containing a single job:
```yaml
stages:
- Building Stuff
- Testing Stuff
.job_base:
  script: ${JOB_RUN_PREFIX} ./pipeline.py run ${INTERNAL_JOB_NAME} ...
Build My App:
  stage: Building Stuff
  extends: .job_base
  variables:
    INTERNAL_JOB_NAME: build_app
Test My App:
  stage: Testing Stuff
  extends: .job_base
  variables:
    INTERNAL_JOB_NAME: test_app
```

## Basic Commandline Arguments
- ```./pipeline.py generate``` to generate `.gitlab-ci.yml`
- ```./pipeline.py list``` to show all stages with their jobs
- ```./pipeline.py run <JOB>``` to run a job (`<JOB>` is the internal job name, e.g. `build_app` in the above example)
- ```./pipeline.py run <JOB> -v MY_VAR="some value"``` to run a job with a variable set to some value

## Documentation
See [docs](./docs):
- [Jobs](./docs/jobs.md)
- [Stages](./docs/stages.md)
- [Variables](./docs/variables.md)
- [Rules & Conditions](./docs/rules.md)
- [Configuration File](./docs/config.md)

## Install
Simply download this repo and run the following command from the repository root:
```bash
pip install .
``` 

## Known Issues
- GitLab docker runners are currently not supported directly. Use the `JobConfig` keyword `yaml_override` to set a docker image.
- not all built-in variables are currently supported, however you can simply add them as user defined variables to a `VariableStore`

## Why?
So why would anyone bother to have an abstraction layer over GitLab YAML files?
The short answer (imo) is this: **Gitlab-CI features are too complex to be efficiently exercised through a markup language.**
In more detail, these are the main reasons:

**Local Pipeline Development:** Creating a pipeline or modifying it can be a daunting task.
You often find yourself committing small changes over and over only to find a typo in a variable or job name.
Creating the pipeline through *spycilab* ensures that the generated YAML is (almost) always valid and that names for jobs, variables, etc. are all consistent.
In addition, there are much better tools (IDEs) for Python that allow you to detect problems in your pipeline definitions on the fly without needing to commit the changes first.

**Local Job Debugging:** When a job fails it is sometimes hard to tell why.
Maybe the software that the job was testing is actually faulty, or was it simply a wrong argument passed to the test script?
When defining a pipeline through *spycilab* you can directly run the jobs on your local machine, making it easier to reproduce errors and to fix them.

**Reusability:** Are you working with multiple projects that have the same or similar pipeline jobs?
While it is possible to reuse Gitlab-CI definitions (e.g. through includes or templates) it can be quite error-prone.
When defining the pipeline through Python, however, you can instead build and reuse modules that define certain aspects of your pipeline.

**Fun:** When taking all of the above aspects together, creating and maintaining pipelines through an abstraction layer simply becomes much more fun.
We've all been there (maybe not all, but you have probably if you're still reading this) repeatedly committing ("test1", "test2", ...) to get the pipeline to do what you want.
*spycilab* aims at minimizing these frustrating steps.

## How does it work?
There is really not much behind the scenes here.
There are simply classes for most GitLab-CI objects (e.g. `Job`) with a `to_yaml()` function that transforms data from Python to YAML.
Type hints and specific runtime checks make sure that issues with the pipeline definitions are detected early on.

