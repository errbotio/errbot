import inspect
import logging
import sys

COLORS = {'DEBUG': 'cyan', 'INFO': 'green', 'WARNING': 'yellow', 'ERROR': 'red', 'CRITICAL': 'red', }

NO_COLORS = {'DEBUG': '', 'INFO': '', 'WARNING': '', 'ERROR': '', 'CRITICAL': '', }


def ispydevd():
    for frame in inspect.stack():
        if frame[1].endswith("pydevd.py"):
            return True
    return False


root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)

pydev = ispydevd()
stream = sys.stdout if pydev else sys.stderr
isatty = pydev or stream.isatty()  # force isatty if we are under pydev because it supports coloring anyway.
console_hdlr = logging.StreamHandler(stream)


def get_log_colors(theme_color=None):
    """Return a tuple containing the log format string and a log color dict"""
    if theme_color == 'light':
        text_color_theme = 'white'
    elif theme_color == 'dark':
        text_color_theme = 'black'
    else:  # Anything else produces nocolor
        return '%(name)-25.25s%(reset)s %(message)s%(reset)s', NO_COLORS

    return f'%(name)-25.25s%(reset)s %({text_color_theme})s%(message)s%(reset)s', COLORS


def format_logs(formatter=None, theme_color=None):
    """
    You may either use the formatter parameter to provide your own
    custom formatter, or the theme_color parameter to use the
    built in color scheme formatter.
    """
    if formatter:
        console_hdlr.setFormatter(formatter)
    # if isatty and not True:
    elif isatty:
        from colorlog import ColoredFormatter  # noqa
        log_format, colors_dict = get_log_colors(theme_color)
        color_formatter = ColoredFormatter(
            "%(asctime)s %(log_color)s%(levelname)-8s%(reset)s " + log_format,
            datefmt="%H:%M:%S",
            reset=True,
            log_colors=colors_dict,
        )
        console_hdlr.setFormatter(color_formatter)
    else:
        console_hdlr.setFormatter(logging.Formatter("%(asctime)s %(levelname)-8s %(name)-25s %(message)s"))
    root_logger.addHandler(console_hdlr)
