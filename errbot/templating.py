import logging
from pathlib import Path

from jinja2 import ChoiceLoader, Environment, FileSystemLoader, PrefixLoader
from markupsafe import Markup

from errbot.plugin_info import PluginInfo

log = logging.getLogger(__name__)


def make_templates_path(root: Path) -> Path:
    return root / "templates"


def _md_table_cell(value) -> str:
    text = str(value)
    # Newlines and pipes would break a Markdown table, so neutralize them.
    text = text.replace("\r\n", " ").replace("\n", " ").replace("\r", " ")
    return text.replace("|", "\\|")


def md_table(rows, headers=None) -> Markup:
    """Render an iterable of rows as a GitHub flavored Markdown table.

    ``rows`` is an iterable of iterables, one per table row. ``headers`` is an
    optional list used for the header row. Cells are turned into strings and any
    pipe or newline characters in them are escaped so the table stays valid.

    The result is a :class:`~markupsafe.Markup` string so it can be dropped
    straight into a Markdown template with ``{{ md_table(rows, headers=[...]) }}``.
    """
    rows = [list(row) for row in rows]
    header_cells = list(headers) if headers is not None else []
    ncols = max([len(header_cells)] + [len(row) for row in rows])
    if ncols == 0:
        return Markup("")

    def line(cells):
        cells = [_md_table_cell(c) for c in cells]
        cells += [""] * (ncols - len(cells))
        return "| " + " | ".join(cells) + " |"

    lines = [line(header_cells), "| " + " | ".join(["---"] * ncols) + " |"]
    lines += [line(row) for row in rows]
    return Markup("\n".join(lines))


system_templates_path = str(make_templates_path(Path(__file__).parent))
template_path = [system_templates_path]
plugin_templates = {}  # plugin_name -> FileSystemLoader


def _recreate_env():
    global env
    loaders = []
    if plugin_templates:
        loaders.append(PrefixLoader(plugin_templates))
    loaders.append(FileSystemLoader(template_path))

    env = Environment(
        loader=ChoiceLoader(loaders),
        trim_blocks=True,
        keep_trailing_newline=False,
        autoescape=True,
    )
    env.globals["md_table"] = md_table


_recreate_env()


def tenv() -> Environment:
    return env


def add_plugin_templates_path(plugin_info: PluginInfo) -> None:
    tmpl_path = make_templates_path(plugin_info.location.parent)
    if tmpl_path.exists():
        log.debug(
            "Templates directory found for %s plugin [%s]", plugin_info.name, tmpl_path
        )
        template_path.append(str(tmpl_path))  # for webhooks
        plugin_templates[plugin_info.name] = FileSystemLoader(str(tmpl_path))

        # Ditch and recreate a new templating environment
        _recreate_env()
        return
    log.debug(
        "No templates directory found for %s plugin in [%s]",
        plugin_info.name,
        tmpl_path,
    )


def remove_plugin_templates_path(plugin_info: PluginInfo) -> None:
    tmpl_path = str(make_templates_path(plugin_info.location.parent))
    changed = False
    if tmpl_path in template_path:
        template_path.remove(tmpl_path)
        changed = True

    if plugin_info.name in plugin_templates:
        del plugin_templates[plugin_info.name]
        changed = True

    if changed:
        # Ditch and recreate a new templating environment
        _recreate_env()
