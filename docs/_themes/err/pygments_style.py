from pygments.style import Style
from pygments.token import Keyword, Name, Comment, String, Error, \
     Number, Operator, Generic, Whitespace, Punctuation, Other, Literal


class ErrStyle(Style):
    """
    A Pygments style based on the "friendly" theme
    """

    background_color = "#ffffcc"
    default_style = ""

    styles = {
        Whitespace:                "#3e4349",
        Comment:                   "#3f6b5b",
        # Comment.Preproc:           "noitalic #007020",
        # Comment.Special:           "noitalic bg:#fff0f0",

        Keyword:                   "bold #f06f00",
        # Keyword.Pseudo:            "nobold",
        # Keyword.Type:              "nobold #902000",

        Operator:                  "#3e4349",
        # Operator.Word:             "bold #007020",

        Name:                      "#3e4349",
        Name.Builtin:              "#007020",
        Name.Function:             "bold #3e4349",
        Name.Class:                "bold #3e4349",
        # Name.Namespace:            "bold #f07e2a",
        # Name.Exception:            "#007020",
        Name.Variable:             "underline #8a2be2",
        Name.Constant:             "underline #b91f49",
        # Name.Label:                "bold #002070",
        Name.Entity:               "bold #330000",
        # Name.Attribute:            "#4070a0",
        Name.Tag:                  "bold #f06f00",
        Name.Decorator:            "bold italic #3e4349",

        # String:                    "#3e4349",
        String:                    "#9a5151",
        # String.Doc:                "italic #3f65b5",
        String.Doc:                "italic #3f6b5b",
        # String.Doc:                "italic #9a7851",
        # String.Doc:                "italic #9a5151",
        # String.Interpol:           "italic #70a0d0",
        # String.Escape:             "bold #4070a0",
        # String.Regex:              "#235388",
        # String.Symbol:             "#517918",
        # String.Other:              "#c65d09",
        Number:                    "underline #9a5151",

        Generic:                   "#3e4349",
        Generic.Heading:           "bold #1014ad",
        Generic.Subheading:        "bold #1014ad",
        Generic.Deleted:           "bg:#c8f2ea #2020ff",
        Generic.Inserted:          "#3e4349",
        # Generic.Error:             "#FF0000",
        # Generic.Emph:              "italic",
        # Generic.Strong:            "bold",
        # Generic.Prompt:            "bold #c65d09",
        # Generic.Output:            "#888",
        # Generic.Traceback:         "#04D",

        # Error:                     "border:#FF0000"
    }
