import sys
import threading
import traceback

def stacktraces():
    from pygments import highlight
    from pygments.lexers import PythonLexer
    from pygments.formatters import TerminalFormatter
    code = []
    for threadId, stack in sys._current_frames().items():
        code.append("\n# ThreadID: %s" % threadId)
        for filename, lineno, name, line in traceback.extract_stack(stack):
            code.append('File: "%s", line %d, in %s' % (filename, lineno, name))
            if line:
                code.append("  %s" % (line.strip()))
    print '-' * 80
    print
    for thread in threading.enumerate():
        print  '%s -> %s\n' % (thread.name, thread.daemon)
    return highlight("\n".join(code), PythonLexer(), TerminalFormatter(
      full=False,
      # style="native",
      noclasses=True))