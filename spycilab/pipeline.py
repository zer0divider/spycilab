##########################
# Author: Cornelius Marx
# Date: November 17th 2024
##########################

import argparse
import sys
import os
import subprocess

from .overridable_yaml_object import OverridableYamlObject
from .variable import Variable, VariableStore
from .job import JobConfig, Job, JobStore
from .stage import Stage, StageStore
from .rule import Rule, When


# NOTE: import yaml only when needed to minimize dependencies in pipeline

class Pipeline(OverridableYamlObject):
    def __init__(self, jobs: JobStore, stages: StageStore, variables: None | VariableStore = None,
                 workflow: list[Rule] = None, yaml_override: dict | None = None):
        super().__init__(yaml_override)
        self.stages = stages
        if variables is None:
            self.vars = VariableStore()
        else:
            self.vars = variables

        self.prefix_flag_name = "--with-prefix"
        self.vars.update_variable_names()
        self.workflow = workflow
        self.jobs = jobs
        self.pipeline_enabled = True
        self.config = None
        self.run_script = "./pipeline.py"
        self.jobs.update_jobs(None)
        self.output = ".gitlab-ci.yml"
        # try loading config files in that order
        self.config_files = [".spycilab.yaml", ".spycilab.yml", ".local.spycilab.yaml", ".local.spycilab.yml"]

    def load_config(self, config_file):
        try:
            with open(config_file, "r") as f:
                import yaml  # import yaml only when needed to minimize dependencies in pipeline
                loader = yaml.Loader(f)
                self.config = loader.get_data()
            if self.config is not None:
                run_script = self.config.get("run_script")
                if run_script is not None:
                    self.run_script = run_script
                output = self.config.get("output")
                if output is not None:
                    self.output = output

                variables = self.config.get("variables")
                if variables is not None:
                    for k, value in variables.items():
                        v = self.vars.get(k)
                        if v is None:
                            raise RuntimeError(f"In file {config_file}: no such variable {k}")
                        v.value = value

            print(f"Loaded config '{config_file}'.")

        except FileNotFoundError:
            pass

    @staticmethod
    def add_variable_argument(sub_parser):
        sub_parser.add_argument("-v", required=False, action="append", help="set a variable (-v VAR=VALUE)")


    @staticmethod
    def add_env_flags(sub_parser):
        sub_parser.add_argument("--no-input-env", required=False, action="store_true",
                                help="Do not set internal variables from system environment.")
        sub_parser.add_argument("--no-forward-env", required=False, action="store_true",
                                help="Do not forward variable values to system environment.")

    def process_variables_from_args(self, variables):
        if variables is not None:
            for v in variables:
                equal_sign_i = v.find("=")
                if equal_sign_i >= 0:
                    var_name = v[:equal_sign_i]
                    var_value = v[equal_sign_i + 1:]
                    current_var = self.vars.__dict__.get(var_name)
                    # check is an actual Variable
                    if not isinstance(current_var, Variable):
                        raise RuntimeError(f"No such variable '{var_name}'")
                    current_var.value = var_value
                else:
                    raise RuntimeError(f"Invalid expression for variable mapping '{v}'. Expected VAR=VALUE")

    def process_variables_from_env(self):
        for v in self.vars.all():
            env_v = os.environ.get(v.name)
            if env_v is not None and isinstance(env_v, str):
                v.value = env_v

    def write_variables_to_env(self):
        # add to environment
        for v in self.vars.all():
            if v.value is not None:
                os.environ[v.name] = v.value

    def check_workflow(self):
        # check workflow
        self.pipeline_enabled = True
        if self.workflow is not None:
            self.pipeline_enabled = False
            for r in self.workflow:
                eval_result = True
                if r.condition is not None:
                    eval_result = r.condition.eval()
                if eval_result:
                    match r.when:
                        case When.never:
                            self.pipeline_enabled = False
                        case None | When.always:
                            self.pipeline_enabled = True
                        case _:
                            raise RuntimeError(f"invalid 'when'-type for pipeline workflow '{r.when}'")
                    break

    def write_output(self):
        import yaml  # import yaml only when needed to minimize dependencies in pipeline
        print(f"writing generated gitlab-ci yaml to '{self.output}'")
        with open(self.output, "w") as f:
            f.write("############################################\n")
            f.write("# AUTOGENERATED BY spycilab - DO NOT EDIT! #\n")
            f.write("############################################\n\n")
            yaml.dump(self.to_yaml(), f, indent=2, sort_keys=False)

    def check_jobs(self):
        all_jobs = list(self.jobs.all())
        for ji, j in enumerate(all_jobs):
            for other_ji in range(ji + 1, len(all_jobs)):
                if j.name == all_jobs[other_ji].name:
                    raise RuntimeError(
                        f"Job '{j.internal_name}' and '{all_jobs[other_ji].internal_name}' have the same name ('{j.name}')")

    def main(self, cmd_args: list[str] | None = None):
        arg_parser = argparse.ArgumentParser(description="This is the pipeline generator and runner.")
        sub_parsers = arg_parser.add_subparsers(required=True, title="subcommands")
        arg_parser.add_argument("--no-input-env", required=False, action="store_true",
                                help="Do not set internal variables from system environment.")
        arg_parser.add_argument("--no-forward-env", required=False, action="store_true",
                                help="Do not forward variable values to system environment.")
        arg_parser.add_argument("--no-config", required=False, action="store_true",
                                help="Do not load config from files (e.g. .spycilab.yaml).")
        # run sub command
        run_arg_parser = sub_parsers.add_parser("run", description="Run a single job from the pipeline.")
        run_arg_parser.add_argument("job", help="internal name of the job to run")
        run_arg_parser.add_argument(self.prefix_flag_name, action="store_true",
                                    help="Starts a subprocess which runs the job with its specified run prefix.")
        run_arg_parser.set_defaults(command="run")
        self.add_variable_argument(run_arg_parser)
        # generate sub command
        gen_arg_parser = sub_parsers.add_parser("generate", description="Generate GitLab-CI YAML file.")
        gen_arg_parser.add_argument("--output", required=False,
                                    help="File to write generated YAML to. This option overrides setting in configuration file.")
        gen_arg_parser.add_argument("--run-script", default=self.run_script,
                                    help="Script to run in generated pipeline. This option overrides setting in configuration file.")
        gen_arg_parser.set_defaults(command="generate")
        # list sub command
        list_arg_parser = sub_parsers.add_parser("list", description="List all pipeline jobs")
        list_arg_parser.set_defaults(command="list")
        list_arg_parser.add_argument("--all", action="store_true", help="Show all jobs, even ones disabled by rules.")
        self.add_variable_argument(list_arg_parser)
        self.args = arg_parser.parse_args(cmd_args)

        if not self.args.no_input_env:
            self.process_variables_from_env()

        if not self.args.no_config:
            for c in self.config_files:
                self.load_config(c)

        if self.args.command == "generate" and self.args.run_script:
            self.run_script = self.args.run_script
        self.jobs.update_jobs(self.run_script)
        self.check_jobs()

        if self.args.__dict__.get("v"):
            self.process_variables_from_args(self.args.v)

        self.vars.check_all()

        if not self.args.no_forward_env:
            self.write_variables_to_env()

        self.check_workflow()

        match self.args.command:
            case "list":
                if not self.pipeline_enabled:
                    print("** Pipeline disabled by workflow rules **\n")
                self.list()
            case "generate":
                if self.args.output:
                    self.output = self.args.output
                self.write_output()
            case "run":
                j = self.jobs.get(self.args.job)
                if j is None:
                    print(f"job '{self.args.job}' does not exist (are you using the internal name?)", file=sys.stderr)
                    exit(1)
                if self.args.with_prefix:
                    if not j.config.run_prefix:
                        print(f"job '{self.args.job}' doesn't have any prefix, running normally ...")
                    else:
                        full_run_cmd = j.get_script()
                        print(f"Running (with prefix): {full_run_cmd}")
                        new_env = os.environ.copy()
                        new_env["SPYCILAB_WITH_PREFIX"] = "true"
                        exit(subprocess.run(full_run_cmd, shell=True, env=new_env).returncode)
                elif j.config.run_prefix and not os.environ.get("SPYCILAB_WITH_PREFIX") == "true":
                    print(f"Warning: job '{self.args.job}' has a run prefix ({j.config.run_prefix}), consider running with flag {self.prefix_flag_name}.")

                exit(self.run(j))
            case _:
                arg_parser.print_help()

    def show_variables(self):
        """
         show all variables that want to be shown
        """
        print(f"CI Variables :")
        for v in self.vars.all():
            if v.show:
                print(f"  {v.name}: ", end="")
                if v.value is None:
                    print(f"<NOT DEFINED>")
                else:
                    print(f"'{v.value}'")
        print("  ... (some may be hidden)\n")

    def list(self):
        self.show_variables()
        jobs_by_stage = {}
        for s in self.stages.all():
            jobs_by_stage[s.name] = []
        for j in self.jobs.all():
            jobs_by_stage[j.config.stage.name].append(j)
        for s in self.stages.all():
            jbs = jobs_by_stage[s.name].copy()
            jbs.sort()
            print(f"{s.name}:")
            for j in jbs:
                mode = When.always
                if j.config.rules:
                    mode = When.never
                    for r in j.config.rules:
                        if r.eval():
                            mode = r.when or When.always
                            break

                if self.args.all or mode != When.never:
                    print(f"  - {j.name} ({j.internal_name}): {mode}")

    def run(self, j: Job) -> int:
        self.show_variables()

        # set specific built-in env variables
        if not self.vars.CI_JOB_NAME.value:
            self.vars.CI_JOB_NAME.value = j.name
        print(f"# Starting job '{j.name}' ({j.internal_name})\n", flush=True)
        job_result = j.run()
        if isinstance(job_result,
                      bool):  # important to check bool first, because 'bool' is a subclass of 'int' (https://peps.python.org/pep-0285/)
            ret = 0 if job_result else 1
        elif isinstance(job_result, int):
            ret = job_result
        else:
            print(f"Warning: Job '{j.internal_name}' did not return bool or integer.", file=sys.stderr)
            ret = 0

        if ret == 0:
            print(f"# Job finished successfully.", flush=True)
        else:
            print(f"# Job FAILED.", flush=True)

        return ret

    def to_yaml_impl(self):
        # collect variables as arguments
        vars_yaml = self.vars.to_yaml()
        p = {}
        # workflow
        if self.workflow is not None:
            rules = []
            for r in self.workflow:
                if r.allow_failure is not None:
                    raise RuntimeError("'allow_failure' should not be set for a workflow rule")
                rules.append(r.to_yaml())
            p["workflow"] = {"rules": rules}

        # variables
        if len(vars_yaml) > 0:
            p["variables"] = vars_yaml

        # stages
        p["stages"] = self.stages.to_yaml()

        zero_width_space = "\u200B"
        stage_orderings = {}
        # Enable Job Sorting
        #   gitlab will always sort jobs in a stage alphabetically,
        #   so the trick is to prepend invisible characters (unicode zero-width-space character)
        #   to adjust the sorting
        for j in self.jobs.all():
            j_stage = j.config.stage
            if j_stage and j_stage.preserve_order:
                if stage_orderings.get(j_stage) is None:
                    stage_orderings[j_stage] = zero_width_space
                j.name = stage_orderings[j_stage] + j.name
                stage_orderings[j_stage] += zero_width_space

        # add jobs
        for j in self.jobs.all():
            p[j.name] = j.to_yaml()
        return p
