from spycilab import VariableStore, Pipeline, Variable, BoolVariable, StageStore, JobStore, Stage, Job, \
    JobConfig, Rule, When


def test_empty_pipeline():
    p = Pipeline(
        jobs=JobStore(),
        stages=StageStore())
    p_yaml = p.to_yaml()
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
    p.jobs.update_jobs(p.run_script)
    p_yaml = p.to_yaml()
    assert p_yaml.get("Build My App") is not None
    assert p_yaml.get("Test My App") is not None
    assert p_yaml.get("stages") == ["Building Stuff", "Testing Stuff"]


def test_preserve_order_in_stage():
    s = StageStore()
    s.stuff = Stage("stuff", preserve_order=True)

    j = JobStore()
    j.C = Job("C", JobConfig(stage=s.stuff))
    j.B = Job("B", JobConfig(stage=s.stuff))
    j.A = Job("A", JobConfig(stage=s.stuff))

    p = Pipeline(jobs=j, stages=s)
    p.jobs.update_jobs(p.run_script)
    p_yaml = p.to_yaml()
    assert p_yaml.get("\u200BC") is not None
    assert p_yaml.get("\u200B\u200BB") is not None
    assert p_yaml.get("\u200B\u200B\u200BA") is not None

    # test whether order-preserving hack works in theory
    l = ["\u200B\u200BA", "\u200BB"]
    l.sort()
    assert l[0] == "\u200BB"


def test_variable():
    # simple variable
    v = Variable(default_value="A", description="This is a normal variable", options=["A", "B"])
    assert v.name is None
    v.name = "v"
    assert v.value == "A"
    assert str(v) == "A"
    assert v.value == v.default_value
    assert v.options == ["A", "B"]

    v_yaml = v.to_yaml()
    assert v_yaml == {"value": v.default_value, "description": v.description, "options": v.options}

    # variable with invalid value
    try:
        v = Variable(default_value="C", options=["A", "B"])
        assert False, "should have thrown"
    except ValueError as e:
        assert "default value must be one of" in str(e).lower()
    try:
        # when passing invalid value from commandline (same as from config)
        var_store = VariableStore()
        var_store.v = Variable(default_value="A", options=["A", "B"])
        Pipeline(jobs=JobStore(), stages=StageStore(), variables=var_store).main(cmd_args=["list", "-v", "v=C"])
        assert False, "should have thrown"
    except ValueError as e:
        assert "invalid value" in str(e).lower()

    # variable with override
    v = Variable("B", description="not final", yaml_override={"description": "realdeal", "hi": "there"})
    v.name = "v2"
    assert v.to_yaml() == {"value": "B", "description": "realdeal", "hi": "there"}

    # test variable boolean eval
    v = Variable(default_value="")
    if v:
        assert False, "The variable should have been evaluated to False"
    v = Variable(default_value="something")
    if not v:
        assert False, "The variable should have been evaluated to True"


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

    # invalid value
    v.value = "yay"
    try:
        b = bool(v)
        assert False, "bool conversion should have thrown"
    except ValueError as e:
        pass

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
    assert e.CI_DEFAULT_BRANCH.value is None


def test_custom_variable_store():
    class MyVarStore(VariableStore):
        def __init__(self):
            super().__init__()
            self.var = Variable("hi")
            self.not_var = 42

    my_var_store = MyVarStore()
    my_var_store.update_variable_names()
    my_var_store.check_all()
    assert my_var_store.not_var == 42
    assert my_var_store.to_yaml()["var"] == "hi"


def test_rule_set_comparison():
    v = Variable("test")
    v.name = "v"
    a = [Rule(v.equal_to("test"))]
    b = [Rule(v.equal_to("test"))]
    assert Rule.sets_equal(a, b)
    b = [Rule(v.equal_to("test"), when=When.never)]
    assert not Rule.sets_equal(a, b)
    b = a
    assert Rule.sets_equal(a, b)
    b = None
    assert not Rule.sets_equal(a, b)
    a = None
    assert Rule.sets_equal(a, b)
