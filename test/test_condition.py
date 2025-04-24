from spycilab import Variable, BoolVariable, Condition

def test_simple():
    var_a = Variable()
    var_a.name = "a"
    var_bool = BoolVariable(True)
    var_bool.name = "c"

    # equal
    var_a.value = "branch_A"
    c = Condition.equal(var_a, "branch_A")
    cv = var_a.equal_to("branch_A")
    assert c.to_yaml() == "($a == 'branch_A')"
    assert cv.to_yaml() == c.to_yaml()
    assert c.eval() == True
    assert cv.eval() == c.eval()
    var_a.value = "branch_B"
    assert c.eval() == False
    assert cv.eval() == c.eval()

    # not equal
    var_a.value = "branch_A"
    c = Condition.not_equal(var_a, "branch_A")
    cv = var_a.not_equal_to("branch_A")
    assert c.to_yaml() == "($a != 'branch_A')"
    assert cv.to_yaml() == c.to_yaml()
    assert c.eval() == False
    assert cv.eval() == c.eval()
    var_a.value = "branch_B"
    assert c.eval() == True
    assert cv.eval() == c.eval()

    # full match
    var_a.value = "branch_A"
    examples_match=["branch_A", "branch_B"]
    examples_not_match=[" branch_A", "branch"]
    c = Condition.full_match(var_a, "branch_.*",
                               examples_match=examples_match,
                               examples_not_match=examples_not_match)
    cv = var_a.full_match("branch_.*", examples_match, examples_not_match)
    assert c.to_yaml() == "($a =~ /^branch_.*$/)"
    assert cv.to_yaml() == c.to_yaml()
    assert c.eval() == True
    assert cv.eval() == c.eval()
    var_a.value = "branch_A"
    assert c.eval() == True
    assert cv.eval() == c.eval()
    var_a.value = " branch_B" # (space at the beginning)
    assert c.eval() == False # not a full match (only partial)
    assert cv.eval() == c.eval()
    var_a.value = "branch"
    assert c.eval() == False
    assert cv.eval() == c.eval()

    # is not empty
    var_a.value = "not_empty"
    c = Condition.defined_and_not_empty(var_a)
    cv = var_a.defined_and_not_empty()
    assert c.to_yaml() == "($a != null && $a != '')"
    assert cv.to_yaml() == c.to_yaml()
    assert c.eval() == True
    assert cv.eval() == c.eval()
    var_a.value = "" # empty
    assert c.eval() == False
    assert cv.eval() == c.eval()
    var_a.value = None # no value
    assert c.eval() == False
    assert cv.eval() == c.eval()

    # is true
    var_bool.set(True)
    c = Condition.is_true(var_bool)
    cv = var_bool.is_true()
    assert c.to_yaml() == "($c == 'yes')"
    assert cv.to_yaml() == c.to_yaml()
    assert c.eval() == True
    assert cv.eval() == c.eval()
    var_bool.set(False)
    assert c.eval() == False
    assert cv.eval() == c.eval()

    # is false
    var_bool.set(True)
    c = Condition.is_false(var_bool)
    cv = var_bool.is_false()
    assert c.to_yaml() == "($c != 'yes')"
    assert cv.to_yaml() == c.to_yaml()
    assert c.eval() == False
    assert cv.eval() == c.eval()
    var_bool.set(False)
    assert c.eval() == True
    assert cv.eval() == c.eval()

def test_variable_to_variable():
    var_a = Variable()
    var_a.name = "a"
    var_b = Variable()
    var_b.name = "b"

    # equal
    var_a.value = "branch_A"
    var_b.value = "branch_B"
    c = Condition.equal(var_a, var_b)
    assert c.to_yaml() == "($a == $b)"
    assert c.eval() == False
    var_a.value = "branch_B"
    assert c.eval() == True

    # equal
    var_a.value = "branch_A"
    var_b.value = "branch_B"
    c = Condition.not_equal(var_a, var_b)
    assert c.to_yaml() == "($a != $b)"
    assert c.eval() == True
    var_a.value = "branch_B"
    assert c.eval() == False

def test_compound():
    var_a = Variable("a")
    var_a.name = "a"
    var_b = Variable("b")
    var_b.name = "b"

    var_a.value = "branch_A"
    var_b.value = "branch_B"
    c = var_a.equal_to("branch_A") & var_b.equal_to("branch_B")
    assert c.to_yaml() == "(($a == 'branch_A') && ($b == 'branch_B'))"
    assert c.eval() == True
    var_b.value = "branch_C"
    assert c.eval() == False
    var_a.value = "branch_C"
    var_b.value = "branch_B"
    assert c.eval() == False
    var_a.value = "branch_A"
    var_b.value = "branch_B"
    assert c.eval() == True
