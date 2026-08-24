from markupsafe import Markup

from errbot.templating import md_table, tenv


def test_md_table_with_headers():
    result = md_table([[1, 2], [3, 4]], headers=["a", "b"])
    assert result == "| a | b |\n| --- | --- |\n| 1 | 2 |\n| 3 | 4 |"


def test_md_table_without_headers_uses_blank_header():
    lines = str(md_table([["x", "y"]])).splitlines()
    assert lines[0] == "|  |  |"
    assert lines[1] == "| --- | --- |"
    assert lines[2] == "| x | y |"


def test_md_table_pads_short_rows():
    lines = str(md_table([["only"]], headers=["a", "b"])).splitlines()
    assert lines[2] == "| only |  |"


def test_md_table_escapes_pipes_and_newlines():
    result = md_table([["a|b", "c\nd"]], headers=["h1", "h2"])
    assert "| a\\|b | c d |" in result


def test_md_table_empty():
    assert md_table([]) == ""


def test_md_table_returns_markup():
    assert isinstance(md_table([["x"]]), Markup)


def test_md_table_available_in_template_env():
    assert "md_table" in tenv().globals
    rendered = (
        tenv()
        .from_string("{{ md_table(rows, headers=cols) }}")
        .render(rows=[["a", "b"]], cols=["c1", "c2"])
    )
    assert rendered == "| c1 | c2 |\n| --- | --- |\n| a | b |"
