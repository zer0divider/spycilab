from spycilab import Variable, Job, Stage, Rule, Artifacts, JobConfig, When, Trigger


def test_simple_job():
    s = Stage("test stage")
    test_list = [1, 2]
    j = Job("my job", JobConfig(stage=s, work=lambda: test_list.append(3) or True))
    j.internal_name = "j"
    j.run_script = "run.py"
    assert j.name == "my job"
    assert j.config.stage.name == "test stage"
    j.run()
    assert test_list == [1, 2, 3]

    j_yaml = j.to_yaml()
    assert j_yaml["stage"] == "test stage"
    assert j_yaml["script"] == "run.py"


def test_complex_job():
    s = Stage("test stage")
    v = Variable("test")
    v.name = "var"
    in_artifact = Artifacts(["in.txt"])
    common_rule = Rule(v.equal_to("test"), when=When.always, allow_failure=True, yaml_override={"changes": None})
    dep_j = Job("first", JobConfig(stage=s, artifacts=in_artifact, rules=common_rule))
    out_artifact = Artifacts(["out.txt"], when=When.on_success)
    dep2_j = Job("second", JobConfig(stage=s, rules=common_rule))
    j = Job("my job",
            JobConfig(stage=s,
                      work=None,
                      rules=[common_rule],
                      artifacts=out_artifact,
                      needs=[in_artifact, dep2_j],
                      tags=["my_tag"],
                      run_prefix="PREFIX",
                      yaml_override={"additional_keyword": ["test1", "test2"]}))
    j.internal_name = "j"
    j.run_script = "run.py"

    j_yaml = j.to_yaml()
    assert j_yaml["stage"] == s.name
    assert len(j_yaml["rules"]) == 1
    assert j_yaml["rules"][0] == {"if": "($var == 'test')", "when": "always", "allow_failure": True, "changes": None}
    assert j_yaml["artifacts"] == {"paths": ["out.txt"], "when": "on_success"}
    assert j_yaml["needs"] == ["first", {"job": "second", "artifacts": False}]
    assert j_yaml["tags"] == ["my_tag"]
    assert j_yaml["script"] == "PREFIX run.py"
    assert j_yaml["additional_keyword"] == ["test1", "test2"]


def test_needs_divergent_rules():
    s = Stage("test stage")
    v = Variable()
    v.name = "v"
    # different rules
    rule1 = Rule(v.equal_to("test"))
    rule2 = Rule(v.equal_to("test2"))
    j1 = Job("Job 1", JobConfig(stage=s, rules=[rule1]))
    j1.internal_name = "j1"
    j1.run_script = "run1"
    j2 = Job("Job 2", JobConfig(stage=s, needs=j1, rules=rule2))
    j2.internal_name = "j2"
    j2.run_script = "run2"
    try:
        j2.to_yaml()
        assert False, "Expected an exception to be thrown."
    except RuntimeError as e:
        assert "rules diverge" in str(e)

    # allowing divergent rules
    j2.config.needs_check_diverging_rules = False
    j2.to_yaml()


def test_extend():
    # extend by single job config
    j_base = JobConfig(tags=["base_tag"])
    j = JobConfig(extends=j_base)
    assert j.tags == ["base_tag"]
    assert j.stage is None

    # extend by single job config, but override
    j = JobConfig(tags=["my_tag"], extends=j_base)
    assert j.tags == ["my_tag"]

    # extend by two job configs
    j_base2 = JobConfig(tags=["base_tag2"])
    j = JobConfig(extends=[j_base, j_base2])
    assert j.tags == ["base_tag2"]
    j = JobConfig(extends=[j_base2, j_base])  # order matters
    assert j.tags == ["base_tag"]

    # extend by two job configs, but override
    j = JobConfig(tags="my_tag", extends=[j_base2, j_base])
    assert j.tags == ["my_tag"]

    # override yaml_override
    j_base = JobConfig(yaml_override={})
    j = JobConfig(yaml_override={"A": "A job", "B": "B job"}, extends=j_base)
    assert j.yaml_override["A"] == "A job"
    assert j.yaml_override["B"] == "B job"
    j_base = JobConfig(yaml_override={"A": "A base job"})
    j = JobConfig(yaml_override={"A": "A job", "B": "B job"}, extends=j_base)
    assert j.yaml_override["A"] == "A job"
    assert j.yaml_override["B"] == "B job"
    j_base = JobConfig(yaml_override={"A": "A base job", "B": "B base job"})
    j = JobConfig(yaml_override={"B": "B job"}, extends=j_base)
    assert j.yaml_override["A"] == "A base job"
    assert j.yaml_override["B"] == "B job"

    # override yaml_override (2 base jobs)
    j_base = JobConfig(yaml_override={"A": "A base job", "B": "B base job"})
    j_base2 = JobConfig(yaml_override={"B": "B base2 job", "C": "C base2 job"})
    j = JobConfig(yaml_override={"B": "B job"}, extends=[j_base, j_base2])
    assert j.yaml_override["A"] == "A base job"
    assert j.yaml_override["B"] == "B job"
    assert j.yaml_override["C"] == "C base2 job"
    j = JobConfig(yaml_override={"A": "A job"}, extends=[j_base, j_base2])
    assert j.yaml_override["A"] == "A job"
    assert j.yaml_override["B"] == "B base2 job"
    assert j.yaml_override["C"] == "C base2 job"


def test_trigger_job():
    stage = Stage("Testing")
    # some basic trigger job
    j = Job("My Job", JobConfig(
        trigger=Trigger(project="my/cool/project", branch="feature-branch", strategy_depend=True),
        stage=stage
    ))
    j.internal_name = "j"
    j.run_script = "run"
    trigger_yaml = j.to_yaml()["trigger"]
    assert trigger_yaml["project"] == "my/cool/project"
    assert trigger_yaml.get("include") is None
    assert trigger_yaml.get("script") is None
    assert trigger_yaml["branch"] == "feature-branch"
    assert trigger_yaml["strategy"] == "depend"
    assert trigger_yaml["forward"]["yaml_variables"] == True
    assert trigger_yaml["forward"]["pipeline_variables"] == False

    # some basic trigger job with setting forward variables and no branch
    j = Job("My Job 2", JobConfig(
        trigger=Trigger(project="my/cool/project",
                        forward_yaml_variables=False, forward_pipeline_variables=True),
        stage=stage
    ))
    j.internal_name = "j"
    j.run_script = "run"
    trigger_yaml = j.to_yaml()["trigger"]
    assert trigger_yaml["project"] == "my/cool/project"
    assert trigger_yaml.get("script") is None
    assert trigger_yaml.get("branch") is None
    assert trigger_yaml.get("strategy") is None
    assert trigger_yaml["forward"]["yaml_variables"] == False
    assert trigger_yaml["forward"]["pipeline_variables"] == True

    # some basic trigger job with include
    j = Job("My Job 2", JobConfig(
        trigger=Trigger(include="some_other_pipeline.yml"),
        stage=stage
    ))
    j.internal_name = "j"
    j.run_script = "run"
    trigger_yaml = j.to_yaml()["trigger"]
    assert trigger_yaml["include"] == "some_other_pipeline.yml"
    assert trigger_yaml.get("script") is None
    assert trigger_yaml.get("branch") is None
    assert trigger_yaml.get("strategy") is None
    assert trigger_yaml["forward"]["yaml_variables"] == True
    assert trigger_yaml["forward"]["pipeline_variables"] == False

    try:
        Trigger(include="some_pipeline.yml", project="some/project")
        assert False
    except ValueError as e:
        pass
