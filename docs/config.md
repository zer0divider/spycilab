# Config File
You can create a `.spycilab.yml` file at the location of the pipeline script to provide a base configuration.
Here are the possible options:
- `run_script`: specify a custom command for the pipeline (default: `./pipeline.py`, overwritten by `--run-script` CLI argument)
- `output`: specify the generated output yml file (default: `.gitlab-ci.yml`, overwritten by `--output` CLI argument)
- `variables`: a dictionary of some default variable definitions for locally executing the pipeline (variable values are overwritten by `-v` CLI argument)

This is an example `.spycilab.yml`:
```yaml
output: .out.gitlab-ci.yml
run_script: "./my_pipeline"
variables:
    CI_DEFAULT_BRANCH: main
    CI_PIPELINE_SOURCE: push
```

## Local Config
Additionally, you can create a `.local.spycilab.yml` file which is supposed to be added by each user (not added to version control)
for testing purposes. This file overrides configurations in the `.spycilab.yml` file.