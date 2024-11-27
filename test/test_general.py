from spycilab import VariableStore, Pipeline, Variable, BoolVariable, StageStore, JobStore, Stage, Job, \
    JobConfig


def test_empty_pipeline():
    p = Pipeline(
        jobs=JobStore(),
        stages=StageStore())
    p_yaml = p.to_yaml()
    job_base = p_yaml.get(".job_base")
    assert job_base is not None
    assert type(job_base.get("script")) is str
    assert job_base.get("script").startswith("${JOB_RUN_PREFIX} ./pipeline.py")
    v = p_yaml.get("variables")
    assert v is None


def test_simple_pipeline():
    # create stages
    s = StageStore()
    s.build = Stage("Building Stuff")
    s.test = Stage("Testing Stuff")

    # create jobs
    j = JobStore()

    j.build_app = Job("Build My App", JobConfig(stage=s.build))
    j.test_app = Job("Test My App", JobConfig(stage=s.test))

    p = Pipeline(jobs=j, stages=s)
    p_yaml = p.to_yaml()
    assert p_yaml.get("Build My App") is not None
    assert p_yaml.get("Test My App") is not None
    assert p_yaml.get("stages") == ["Building Stuff", "Testing Stuff"]


def test_variable():
    # simple variable
    v = Variable(default_value="A", description="This is a normal variable", options=["A", "B"])
    assert v.name is None
    v.name = "v"
    assert v.value == "A"
    assert str(v) == "v"
    assert v.value == v.default_value
    assert v.options == ["A", "B"]

    v_yaml = v.to_yaml()
    assert v_yaml == {"value": v.default_value, "description": v.description, "options": v.options}

    # variable with override
    v = Variable("B", description="not final", yaml_override={"description": "realdeal", "hi": "there"})
    v.name = "v2"
    assert v.to_yaml() == {"value": "B", "description": "realdeal", "hi": "there"}


def test_bool_variable():
    # simple variable
    v = BoolVariable(default_value=True, description="This is a normal variable")
    assert v.name is None
    v.name = "b"
    assert v.value == "yes"
    assert v.options == ["yes", "no"]
    assert bool(v) == True
    v.set(False)
    assert bool(v) == False

    v_yaml = v.to_yaml()
    assert v_yaml == {"value": v.default_value, "description": v.description, "options": ["yes", "no"]}


def test_variable_store():
    e = VariableStore()
    e.MY_VARIABLE = Variable("hi")
    e.update_variable_names()
    # check built-ins
    for b in VariableStore.BUILTINS:
        v = e.__dict__.get(b)
        # if one of these asserts fail, check BUILTINS and declared variables in Environment class
        assert v is not None
        assert v.name == b
    assert e.to_yaml() == {"MY_VARIABLE": "hi"}
    assert e.CI_DEFAULT_BRANCH.value == "main"
