# Rules and Conditions
The class `Rule` is a helper object for defining the `rules` keyword of a job or workflow.
A `Rule` is built from an optional condition (one or none) and some other options (e.g. `when`, `allow_failure`).
A `Condition` sets the `if` part of the rule.
```python
rule_only_on_test = Rule(Condition.equal(variables.CI_COMMIT_BRANCH, "test-branch"), when=When.always)
jobs.test_job = Job("Test Job", JobConfig(rules=rule_only_on_test, ...)) # this job only runs on commits to branch 'test-branch'
```
generates
```yaml
Test Job:
  rules:
    - if: $CI_COMMIT_BRANCH == 'test-branch'
      when: "always"
  ...
```
Other comparision functions are:
- `Condition.not_equal(var, other)` variable value is not equal to other variable or string
- `Condition.is_empty(var)` variable value is empty string (**note**: this is different from a variable not set)
- `Condition.is_not_empty(var)` variable value is not empty string
- `Condition.is_set(var)` variable value is set and not empty string (in yaml this is just the variable itself, e.g. `if: $CI_COMMIT_TAG`)
- `Condition.is_true(bool_var)` bool variable value is true (`yes`)
- `Condition.is_false(bool_var)` bool variable value is false (`no`)
- `Condition.full_match(var, pattern)` variable fully matches a given regular expression
  - this one has two additional options `examples_match` and `examples_not_match` as sanity-check for which you can pass a bunch of values that are expected to match/not match

## Conditions from Variable
Instead of using `Condition.equal()` (or similar) the `Variable` class has functions to build a `Condition` object directly:
```python
variables.CI_COMMIT_BRANCH.equal_to("test-branch")
```

## Built-in Conditions
In the `VariableStore` class you can find some useful condition creator functions:
```python
variables.pipeline_source_is(source) # e.g. PipelineSource.push
variables.branch_is_default() # CI_COMMIT_BRANCH == CI_DEFAULT_BRANCH
# ...
```
