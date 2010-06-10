"""Handy dandy routines for exercising yer code.

Use exercise() to try things that shouldn't fail, or things that should
fail with a known exception, and raise an exception only if an
unanticipated exception is encountered.

Use note() to emit an error message to standard error."""

__version__ = "$Revision: 2.8 $"

TestFailure = 'TestFailure'

def note(msg, *args):
    """Emit message to stderr, formatting message string with optional args."""
    import sys
    sys.stderr.write(msg % args + '\n')

def exercise(stmt, env, purpose, expected_exception=None, verbose=0):
    """Exec a statement in an environment, catching expected exceptions if any.

    Exec STATEMENT in ENV.

    PURPOSE describes the statements intended effect, for failure reports.

    Optional EXPECTED_EXCEPTION indicates exception that code is *supposed*
    to raise.

    If optional VERBOSE is set, note() exec of the statement."""
    
    import sys

    try:
        if verbose: note("Exercise: exec %s in env", `stmt`)
        exec stmt in env
        if expected_exception:
            raise TestFailure, ("Unanticipated success, %s (%s)"
                                % (`stmt`, purpose))
        return
    except:
        if sys.exc_type == expected_exception:
            return
        else:
            raise sys.exc_type, sys.exc_value, sys.exc_traceback

ModEnv = vars()
def test_exercise(verbose=0):
    """Exercise exercise, and demonstrate usage..."""
    env = ModEnv
    exercise('testee = 1',
             env, "Innocuous assignment", None, verbose)
    exercise('if testee != 1: raise SystemError, "env not working"',
             env, "Verify assignment", None, verbose)
    exercise('x(1) = 17',
             env, "Expecting basic syntax error", SyntaxError, verbose)
    exercise('{}[1]',
             env, "Expecting basic key error.", KeyError, verbose)

    env['env'] = env
    exercise("""exercise('1', env, 'Falsely expecting syntax error',
                         SyntaxError, %d)""" % verbose,
             env, "Capturing exercise exercise error", TestFailure, verbose)

    print 'test_exercise() passed.'

if __name__ == "__main__":

    test_exercise()
