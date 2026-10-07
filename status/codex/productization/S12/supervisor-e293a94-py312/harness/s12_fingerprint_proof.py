"""A successful child test is insufficient without cleanup and unchanged inputs."""
def bound_result(result, *, tree_reaped, inputs_unchanged):
    facts=dict(result.__dict__)
    facts['test_result_passed']=result.passed
    facts['passed']=result.passed is True and tree_reaped is True and inputs_unchanged is True
    return facts
