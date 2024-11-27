##########################
# Author: Cornelius Marx
# Date: November 17th 2024
##########################

import argparse
import sys

from .overridable_yaml_object import OverridableYamlObject
from .variable import Variable, VariableStore
from .job import JobConfig, Job, JobStore
from .stage import Stage, StageStore
from .rule import Rule, When
import yaml

class Pipeline(OverridableYamlObject):
    def __init__(self, jobs: JobStore, stages: StageStore, variables: None | VariableStore = None, workflow: list[Rule] = None, yaml_override: dict | None = None):
        super().__init__(yaml_override)
        self.stages = stages
        if variables is None:
            self.vars = VariableStore()
        else:
            self.vars = variables

        self.vars.update_variable_names()
        self.workflow = workflow
        self.jobs = jobs
        self.jobs.update_jobs()
        self.pipeline_enabled = True
        self.config = None
        self.run_script = "./pipeline.py"
        self.output = ".gitlab-ci.yml"

    def load_config(self):
        try:
            with open(".spycilab.yml", "r") as f:
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
                    for k,value in variables.items():
                        v = self.vars.get(k)
                        if v is None:
                            raise RuntimeError(f"no such variable {k}")
                        v.value = value

        except FileNotFoundError:
            pass

    @staticmethod
    def add_variable_argument(sub_parser):
        sub_parser.add_argument("-v", required=False, action="append", help="set a variable (-v VAR=VALUE)")

    def check_variables(self, variables):
        if variables is not None:
            for v in variables:
                equal_sign_i = v.find("=")
                if equal_sign_i >= 0:
                    var_name = v[:equal_sign_i]
                    var_value = v[equal_sign_i + 1:]
                    if not isinstance(self.vars.__dict__.get(var_name), Variable):
                        raise RuntimeError(f"No such variable '{var_name}'")
                    self.vars.__dict__[var_name].value = var_value
                else:
                    raise RuntimeError(f"Invalid expression for variable mapping '{v}'. Expected VAR=VALUE")

    def check_workflow(self):
        # check workflow
        self.pipeline_enabled = True
        if self.workflow is not None:
            self.pipeline_enabled = False
            for r in self.workflow:
                if r.condition.eval():
                    match r.when:
                        case When.never:
                            self.pipeline_enabled = False
                        case When.always:
                            self.pipeline_enabled = True
                        case _:
                            raise RuntimeError(f"invalid 'when'-type for pipeline workflow '{r.when}'")
                    break

    def write_output(self):
        print(f"writing generated gitlab-ci yaml to '{self.output}'")
        with open(self.output, "w") as f:
            f.write("############################################\n")
            f.write("# AUTOGENERATED BY spycilab - DO NOT EDIT! #\n")
            f.write("############################################\n\n")
            yaml.dump(self.to_yaml(), f, indent=2, sort_keys=False)

    def check_jobs(self):
        all_jobs = list(self.jobs.all())
        for ji, j in enumerate(all_jobs):
            cmp = j.name
            for other_ji in range(ji+1, len(all_jobs)):
                if j.name == all_jobs[other_ji].name:
                    raise RuntimeError(f"Job '{j.internal_name}' and '{all_jobs[other_ji].internal_name}' have the same name ('{j.name}')")

    def main(self, cmd_args: list[str] | None = None):
        arg_parser = argparse.ArgumentParser(description="This is the pipeline generator and runner.",
                                             epilog="Call with no arguments to generate gitlab-ci yaml." )
        sub_parsers = arg_parser.add_subparsers(required=True, title="subcommands")
        # run sub command
        run_arg_parser = sub_parsers.add_parser("run", description="Run a single job from the pipeline.")
        run_arg_parser.add_argument("job", help="internal name of the job to run")
        run_arg_parser.set_defaults(command="run")
        self.add_variable_argument(run_arg_parser)
        # generate sub command
        gen_arg_parser = sub_parsers.add_parser("generate", description="Generate GitLab-CI YAML file.")
        gen_arg_parser.add_argument("--output", required=False, help="File to write generated YAML to. This option overrides setting in configuration file.")
        gen_arg_parser.set_defaults(command="generate")
        # list sub command
        list_arg_parser = sub_parsers.add_parser("list", description="List all pipeline jobs")
        self.add_variable_argument(list_arg_parser)
        list_arg_parser.set_defaults(command="list")
        args = arg_parser.parse_args(cmd_args)

        self.load_config()

        self.check_jobs()

        if args.__dict__.get("v"):
            self.check_variables(args.v)

        self.check_workflow()

        if not self.pipeline_enabled:
            print("** Pipeline disabled by workflow rules **\n")

        match args.command:
            case "list":
                self.list()
            case "generate":
                if args.output:
                    self.output = args.output
                self.write_output()
            case "run":
                self.run(args.job)
            case _:
                arg_parser.print_help()

    def list(self):
        jobs_by_stage = {}
        for s in self.stages.all():
            jobs_by_stage[s.name] = []
        for j in self.jobs.all():
            jobs_by_stage[j.config.stage.name].append(j)
        for s in self.stages.all():
            jbs = jobs_by_stage[s.name]
            print(f"{s.name}: ({len(jbs)})")
            for j in jbs:
                mode = When.always
                if j.config.rules:
                    mode = When.never
                    for r in j.config.rules:
                        if r.eval():
                            mode = r.when
                            break

                if mode != When.never:
                    print(f"  - {j.name} ({mode})")

    def run(self, job: str):
        j = self.jobs.get(job)
        if j is None:
            print(f"job '{job}' does not exist", file=sys.stderr)
            exit(1)
        else:
            # set specific built-in env variables
            self.vars.CI_JOB_NAME.value = j.name
            j.run()

    def to_yaml_impl(self):
        var_args = []
        vars_yaml = self.vars.to_yaml()
        for e in self.vars.all():
            var_args.append('-v ' + e.name + '="${' + e.name + '}"')
        p = {}
        # workflow
        if self.workflow is not None:
            p["workflow"] = {"rules": [r.to_yaml(is_workflow=True) for r in self.workflow]}

        # variables
        if len(vars_yaml) > 0:
            p["variables"] = vars_yaml

        # stages
        p["stages"] = self.stages.to_yaml()

        # job base
        p[".job_base"] = {"script": "${JOB_RUN_PREFIX} "+self.run_script+" run ${INTERNAL_JOB_NAME} " + " ".join(var_args)}

        # add jobs
        for j in self.jobs.all():
            p[j.name] = j.to_yaml()
        return p
