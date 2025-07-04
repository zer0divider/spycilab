# Jobs
Jobs are defined by a name and a `JobConfig`.
The name is the actual name displayed in the pipeline.
Jobs have to be added to a `JobStore` in order to be recognized by the pipeline.
There are two ways of adding jobs to a `JobStore`.

**static**:
```python
jobs = JobStore()
jobs.my_job = Job("This is My Job", JobConfig(...))
jobs.my_other_job = Job("This is My Other Job", JobConfig(...))
```

**dynamic**:
```python
jobs = JobStore()
# adding jobs dynamically
for i in range(3):
    jobs.add(f"job_{i}", Job(f"This is Job {i}", JobConfig(...)))

# retrieve jobs dynamically
jobs.get("job_2")
```
Statically added jobs can also be retrieved dynamically.

## Work
In *spycilab* the stuff a job does is called `work` (defined through the `JobConfig`).
The callable should return an error code (integer) or a boolean indicating whether the job was successful.
It is simply a callable object (e.g. a function) that is called when the job runs.
Here are some examples:
```python
def my_job_work():
    print("Do stuff...")

# work with function
jobs.my_job = Job("My Job", JobConfig(work=my_job_work))

# work with lambda
jobs.my_other_job = Job("My Job", JobConfig(
    work=lambda: print("doing work ...") or True  # 'or True' needed so the work returns a value (encouraged)
))
```
The work can also be defined after the job instantiation through the `job_work` decorator.
```python
jobs.my_job = Job("My Job", JobConfig())

@job_work(jobs.my_job)
def my_job_work():
    print("Do other stuff...")
    return True
```

### Parameterization
If you want to create multiple jobs using the same work function (but with different arguments) you have to be careful as python likes to
use references for the parameters accessed in a lambda. The following example shows how NOT to do it:
```python
def show_value(value:int):
    print("The value is", value)
    return True
    
for i in range(3):
    jobs.add(f"show_value_{i}", Job(f"Show Value {i}", JobConfig(
        work=lambda: show_value(i)  # a reference to 'i' is stored in the lambda,
                                    # not the current value of 'i'
        ...
    )))
```
No matter which job you run (`show_value_0`, `show_value_1` or `show_value_2`), they will all print `The value is 2`.
This is because the last value `i` was set to is `2` when the work functions are called (`i` is used as reference in the lambda).

To fix this, put the job creation in a function with a parameter to pass onto the work function, like so: 
```python
def show_value(value:int):
    print("The value is", value)
    return True

def create_show_job(value:int):
    jobs.add(f"show_value_{value}", Job(f"Show Value {value}", JobConfig(
        work=lambda: show_value(value)  # 'value' is still used as reference, however,
                                        # each invocation of 'create_show_job()' has it's own 'value' variable
                                        # each assigned to a different value
        ...
    )))

for i in range(2):
    create_show_job(i)
```
Now each job prints its corresponding value correctly (e.g. `show_value_1` prints `The value is 1`).

## Needs
The `needs` keyword in *spycilab* is a little bit different from the native GitLab-CI yaml `needs` as it expects a list of artifacts or jobs.
The actual job that produces the artifact is automatically referenced when artifacts are specified.
If a job is specified in `needs` no artifacts are downloaded (`artifacts: false`).
```python
file = Artifacts(paths=["file.txt"], when=When.always)
jobs.producer1_job = Job("Producer1", JobConfig(artifacts=file, ...))
jobs.producer2_job = Job("Producer2", JobConfig(...))
jobs.consumer_job = Job("Consumer", JobConfig(needs=[file, jobs.producer2_job], ...))
```
generates
```yaml
Producer1:
  artifacts:
    paths: ["file.txt"]
    when: always
  ...
  
Producer2:
  ...

Consumer:
  needs:
  - "Producer1"
  - job: "Producer2"
    artifacts: false
  ...
    
```

## Trigger Job
A trigger job can be specified through the `trigger` keyword of the `JobConfig`. Here is an example:
```python
jobs.trigger_job = Job("Trigger Downstream Pipeline",
  JobConfig(trigger=Trigger(project="path/to/other/project", strategy_depend=True), ...)
)
```
generates
```yaml
Trigger Downstream Pipeline:
  trigger:
    project: "path/to/other/project"
    strategy: depend
  ...
```

## Base Configurations and Inheritance (extends)
The `extends` keyword functionally works like the native GitLab-CI yaml, however it expects a list of `JobConfig` objects and
ultimately does not generate an `extends` keyword in the yaml.
Instead, the configurations the job is extended by are expanded in the final yaml.
```python
config_my_tag = JobConfig(when=When.always, tags=["my_tag"])
jobs.my_job = Job("My Job", JobConfig(when=When.manual, extends=[config_my_tag]))
```
generates
```yaml
My Job:
  tags: [ "my_tag" ]
  when: "manual"
```
You can also extend a job configuration by deriving the `Job` class.
This way you can perform operations not possible by the simple `extend` keyword.
For example **adding** a specific tag (`extends` would only allow you to set all tags, not to add one to the list of tags defined by the derived job):
```python
# always adds 'my_tag' to tags
class MyTagJob(Job):
    def __init__(self, name:str, config:JobConfig):
        adjusted_config = config.copy() # make a copy to not alter config, as it may be used in other jobs as well
        if adjusted_config.tags is None:
            adjusted_config.tags = []
        if "my_tag" not in adjusted_config.tags:
            adjusted_config.tags.append("my_tag")
        super().__init__(name, adjusted_config)

jobs.my_job = MyTagJob("My Job", JobConfig(tags="other_tag"))
```
generates
```yaml
My Job:
  tags: [ "my_tag", "other_tag" ]
```

## Run Prefix
The `run_prefix` keyword in the `JobConfig` prepends the call to the pipeline script (`./pipeline.py`) with a custom string.
This might be useful, for example, to run the job in a docker container.
```python
jobs.docker_job = Job("Docker Job", JobConfig(run_prefix="docker run my_image"))
```
generates
```yaml
Docker Job:
  script: docker run my_image ./pipeline.py run docker_job
```

## Additional Keywords
Most of the keywords (`needs`, `rules`, etc.) have already been implemented in the `JobConfig`.
For other GitLab-CI keywords that are not directly supported, use the `yaml_override` dictionary:
```python
JobConfig(yaml_override={"before_script": "echo 'Hello World'"})
```
When the yaml is generated keywords defined in the `yaml_override` are simply added (be careful: no checks are performed here!).
These keywords will override (hence the name) other keywords of the `JobConfig`, so
```python
jobs.my_job = Job("My Job", JobConfig(needs=[jobs.other_job], yaml_override={"needs": ["something else"]}))
```
generates
```yaml
My Job:
  ...
  needs: [ "something else" ]
  ...
```