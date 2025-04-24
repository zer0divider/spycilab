import subprocess
import pathlib
import yaml
import os
import pytest

pipeline_dir = pathlib.Path(__file__).parent / "resources"
pipeline_script = str(pipeline_dir / "pipeline.py")


@pytest.fixture
def pipeline_yaml():
    """
    generates yaml and cleans up afterwards
    """
    output_file = "test_pipeline.yaml"
    subprocess.run([pipeline_script, "generate", "--output", output_file], check=True)
    yield output_file
    os.remove(output_file)

def create_config(file:str, content:dict):
    with open(file, "w") as f:
        yaml.dump(content, f)
    yield content
    os.remove(file)

@pytest.fixture
def pipeline_config():
    yield from create_config(".spycilab.yml", {"variables": {"test_variable": "FromConfig"}})

@pytest.fixture
def pipeline_local_config():
    yield from create_config(".local.spycilab.yml", {"variables": {"test_variable": "FromLocalConfig"}})


def test_generate(pipeline_yaml):
    with open(pipeline_yaml, "r") as f:
        p_yaml = yaml.Loader(f).get_data()

    # variables
    assert p_yaml["variables"]["test_variable"]["value"] == "my_default"
    assert p_yaml["variables"]["test_variable"]["description"] == "This is a test variable."

    # stages
    assert p_yaml["stages"] == ["Testing"]

    # jobs
    assert p_yaml["Unit Tests"]["stage"] == "Testing"
    assert p_yaml["Unit Tests"]["script"] == "./pipeline.py run test"
    assert p_yaml["Unit Tests"]["rules"][0]["if"] == "(($test_variable == 'A') || ($test_variable == 'B'))"
    assert p_yaml["Unit Tests"]["rules"][0]["when"] == "always"

    assert p_yaml["Always Fails"]["stage"] == "Testing"

    # workflow
    assert p_yaml["workflow"]["rules"][0]["if"] == "($CI_COMMIT_BRANCH == 'master')"
    assert p_yaml["workflow"]["rules"][1]["if"] == "($CI_COMMIT_TAG =~ /^skip-.*$/)"
    assert p_yaml["workflow"]["rules"][1]["when"] == "never"

@pytest.fixture
def env_var():
    os.environ["test_variable"] = "set from env"
    yield os.environ["test_variable"]
    del os.environ["test_variable"]

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

def test_run_with_env(env_var):
    # variable from environment
    r = subprocess.run([pipeline_script, "run", "test"], check=True, capture_output=True)
    output = r.stdout.decode()
    assert f"testing stuff (var='{env_var}')..." in output

    # env vars are forwarded to subprocesses in pipeline (should be built-in feature of python)
    r = subprocess.run([pipeline_script, "run", "subprocess"], check=True, capture_output=True)
    output = r.stdout.decode()
    assert f"from subprocess: {env_var}" in output

    # vars set via commandline are forwarded to environment
    r = subprocess.run([pipeline_script, "run", "subprocess", "-v", "test_variable=from_cmdline"], check=True, capture_output=True)
    output = r.stdout.decode()
    assert f"from subprocess: from_cmdline" in output

    # --no-input-env (environment is ignored as input)
    r = subprocess.run([pipeline_script, "--no-input-env", "run", "test"], check=True, capture_output=True)
    output = r.stdout.decode()
    assert f"testing stuff (var='my_default')..." in output

    # --no-forward-env (vars set via commandline are not forwarded to environment)
    r = subprocess.run([pipeline_script, "--no-forward-env", "run", "subprocess", "-v", "test_variable=not_forwarded"], check=True, capture_output=True)
    output = r.stdout.decode()
    assert f"from subprocess: {env_var}" in output
    assert "not_forwarded" not in output

def test_run_with_config(pipeline_config):
    # config loaded
    r = subprocess.run([pipeline_script, "run", "test"], check=True, capture_output=True)
    output = r.stdout.decode()
    var_value = pipeline_config["variables"]["test_variable"]
    assert f"testing stuff (var='{var_value}')..." in output

def test_run_with_local_config(pipeline_config, pipeline_local_config):
    # local config loaded and overwrites normal config
    r = subprocess.run([pipeline_script, "run", "test"], check=True, capture_output=True)
    output = r.stdout.decode()
    var_value = pipeline_local_config["variables"]["test_variable"]
    assert f"testing stuff (var='{var_value}')..." in output

def test_run_with_prefix():
    # job succeeds
    r = subprocess.run([pipeline_script, "run", "--with-prefix", "prefix" ], check=True, capture_output=True)
    stdout = r.stdout.decode()
    stderr = r.stderr.decode()
    assert "Running with prefix: time --portability" in stdout
    # check output from command 'time'
    assert "real 1." in stderr # job runs for roughly 1 second
    assert "user" in stderr
    assert "sys" in stderr


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

test_list_with_var_expected = """\
Testing:
  - Always Fails (fail): always
  - Unit Tests (test): always
"""

def test_list_with_var():
    o = pipeline_list(["-v", "test_variable=A"])
    assert test_list_with_var_expected in o

test_list_all_expected = """\
Testing:
  - Always Fails (fail): always
  - Prefix Job (prefix): never
  - Subprocess Job (subprocess): never
  - Unit Tests (test): never
"""

def test_list_all():
    # all jobs
    o = pipeline_list(["--all"])
    assert test_list_all_expected in o
