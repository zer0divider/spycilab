# Stages
Stages are created and maintained in a `StageStore`.
```python
stages = StageStore()
stages.test = Stage("Testing")
stages.deploy = Stage("Deploying")

```

Jobs then directly reference that stage object.
```python
Job("Run Unit Tests", JobConfig(stage=stages.test, ...))
```
This way the *Run Unit Tests* job will appear in stage *Testing*.

## Preserve Job Order
One annoying issue with GitLab is that jobs within a stage are always sorted alphabetically by name.
If you want your jobs to appear in a certain order *spycilab* has a nice workaround for you.
By setting `preserve_order=True` in the stage constructor jobs of that stage will appear in the order you declare them in, no matter their name.

```python
stages.test = Stage("Testing (order preserved)", preserve_order=True)
stages.deploy = Stage("Deploying (order not preserved)", preserve_order=False)

jobs.a = Job("B", JobConfig(stage=stages.test))
jobs.b = Job("A", JobConfig(stage=stages.test))

jobs.d = Job("D", JobConfig(stage=stages.deploy))
jobs.c = Job("C", JobConfig(stage=stages.deploy))
```

Results in the pipeline:

| Testing (order preserved) | Deploying (order not preserved) |
|---------------------------|---------------------------------|
| B                         | C                               |
| A                         | D                               |

**Note**: This hack works by adjusting the final names of the jobs by prepending invisible unicode characters (`\u200B`).
So if for some reason you need the job names to stay exactly as you declare them, this option won't work for you.