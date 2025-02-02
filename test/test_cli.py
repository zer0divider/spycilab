import subprocess
import pathlib
import yaml
import os
import pytest

pipeline_script = str(pathlib.Path(__file__).parent / "resources" / "pipeline.py")


@pytest.fixture
def pipeline_yaml():
    """
    generates yaml and cleans up afterwards
    """
    output_file = "test_pipeline.yaml"
    subprocess.run([pipeline_script, "generate", "--output", output_file], check=True)
    yield output_file
    os.remove(output_file)


def test_generate(pipeline_yaml):
    with open(pipeline_yaml, "r") as f:
        p_yaml = yaml.Loader(f).get_data()

    # variables
    assert p_yaml["variables"]["test_variable"]["value"] == "my_default"
    assert p_yaml["variables"]["test_variable"]["description"] == "This is a test variable."

    # stages
    assert p_yaml["stages"] == ["Testing"]

    # jobs
    assert p_yaml[".job_base"]["script"].startswith("${JOB_RUN_PREFIX} ./pipeline.py run ${INTERNAL_JOB_NAME}")
    assert p_yaml["Unit Tests"]["stage"] == "Testing"
    assert p_yaml["Unit Tests"]["extends"] == ".job_base"
    assert p_yaml["Unit Tests"]["variables"]["INTERNAL_JOB_NAME"] == "test"
    assert p_yaml["Unit Tests"]["rules"][0]["if"] == "(($test_variable == 'A') || ($test_variable == 'B'))"
    assert p_yaml["Unit Tests"]["rules"][0]["when"] == "always"

    assert p_yaml["Always Fails"]["stage"] == "Testing"
    assert p_yaml["Always Fails"]["extends"] == ".job_base"
    assert p_yaml["Always Fails"]["variables"]["INTERNAL_JOB_NAME"] == "fail"

    # workflow
    assert p_yaml["workflow"]["rules"][0]["if"] == "($CI_COMMIT_BRANCH == 'master')"
    assert p_yaml["workflow"]["rules"][1]["if"] == "($CI_COMMIT_TAG =~ /^skip-.*$/)"
    assert p_yaml["workflow"]["rules"][1]["when"] == "never"


def test_run():
    # job succeeds
    r = subprocess.run([pipeline_script, "run", "test", "-v", "test_variable=hi"], check=True, capture_output=True)
    output = r.stdout.decode()
    assert "testing stuff (var='hi')..." in output
    assert "Starting job 'Unit Tests' (test)" in output
    assert "Job finished successfully" in output

    # job fails
    r = subprocess.run([pipeline_script, "run", "fail"], capture_output=True)
    output = r.stdout.decode()
    assert "Job FAILED" in output
    assert r.returncode == 1


def pipeline_list(additional_params:list[str]|None=None) -> str:
    """
    helper function to list jobs in test pipeline
    :return: listed jobs as string
    """
    params = [pipeline_script, "list"]
    if additional_params is not None:
        params.extend(additional_params)
    r = subprocess.run(params, check=True, capture_output=True)
    return r.stdout.decode()


def test_list_simple():
    # one job deactivated
    o = pipeline_list()
    assert "Testing:\n  - Always Fails (fail): always" in o
    assert "Unit Tests (test): always" not in o


def test_list_with_var():
    # all jobs
    o = pipeline_list(["-v", "test_variable=A"])
    assert "Testing:\n  - Always Fails (fail): always\n  - Unit Tests (test): always" in o


def test_list_all():
    # all jobs
    o = pipeline_list(["--all"])
    assert "Testing:\n  - Always Fails (fail): always\n  - Unit Tests (test): never" in o
