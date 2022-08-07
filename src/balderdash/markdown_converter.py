"""
Copyright (c) 2014, Aaron O'Leary (dev@aaren.me)
All rights reserved.

Redistribution and use in source and binary forms, with or without modification,
are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this
   list of conditions and the following disclaimer.
2. Redistributions in binary form must reproduce the above copyright notice, this
   list of conditions and the following disclaimer in the documentation and/or
   other materials provided with the distribution.
   
THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT,
INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE
OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF
ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

The MarkdownReader class is adapted from Aaron O'Leary's notedown package:
https://github.com/aaren/notedown/blob/master/notedown/notedown.py
"""

import re
from black import format_str, FileMode
from pathlib import Path
from textwrap import dedent

from pandocattributes import PandocAttributes

# import dash_core_components as dcc


class MarkdownConverter:
    """Import markdown to IPython Notebook.
    The markdown is split into blocks: code and not-code. These
    blocks are used as the source for cells in the notebook. Code
    blocks become code cells; not-code blocks become markdown cells.
    Only supports two kinds of notebook cell: code and markdown.
    """

    # type identifiers
    code = "code"
    markdown = "markdown"

    # regular expressions to match a code block, splitting into groups
    # N.B you can't share group names between these patterns.
    # this is necessary for format agnostic code block detection.
    # These two pattern strings are ORed to create a master pattern
    # and the python re module doesn't allow sharing group names
    # in a single regular expression.
    re_flags = re.MULTILINE | re.VERBOSE

    # the regex that captures code blocks
    code_regex = r"""
    ^(?P<raw>
    (?P<fence>`{3})         # a line starting with a fence of 3 `
    [ \t]*                  # followed by any amount of whitespace,
    \{(?P<attributes>.*)\}  # the 'attributes' surrounded by braces,
    \n?                     # optional newline,
    (?P<content>            # the 'content' group,
    [\s\S]*?)               # that includes anything
    \n?                     # optional newline
    (?P=fence)$\n)          # up until the same fence that we started with
    """

    # classes that will be applied to all Markdown components
    markdown_classes = ["dash-markdown"]

    # classes that will be applied to all dash layout components
    dash_layout_classes = ["dash-layout"]

    def __init__(
        self,
        code_regex=None,
        precode="",
        app_precode="",
        markdown_classes=None,
        dash_layout_classes=None,
        app_path=".",
        indent="    ",
    ):
        """
        code_regex - Custom regex for defining code blocks
        precode    - string, lines of code to put at the start of the
                     document, e.g.
                     '%matplotlib inline\nimport numpy as np'
        """
        self.precode = precode
        self.indent = indent
        self.app_precode = app_precode
        self.app_path = Path(app_path)

        if code_regex is not None:
            self.code_regex = code_regex
        if markdown_classes is not None:
            self.markdown_classes = markdown_classes
        if dash_layout_classes is not None:
            self.dash_layout_classes = dash_layout_classes

        self.code_pattern = re.compile(self.code_regex, self.re_flags)

    def new_code_block(self, **kwargs):
        """Create a new code block."""
        proto = {"content": "", "type": self.code, "IO": "", "attributes": ""}
        proto.update(**kwargs)
        return proto

    def new_text_block(self, **kwargs):
        """Create a new text block."""
        proto = {"content": "", "type": self.markdown}
        proto.update(**kwargs)
        return proto

    @staticmethod
    def preprocess_dash_content(content):
        """Preprocess the content of a Dash block"""
        # does nothing currently,
        return content

    @staticmethod
    def preprocess_markdown(content):
        """Get preprocessed Markdown content"""
        return content.strip()

    @staticmethod
    def make_markdown_component(content, component_id=None, classes=None):
        kwargs = {}
        if content:
            kwargs["children"] = f'"""\n{content}"""'
        if component_id:
            kwargs["id"] = component_id
        if classes:
            all_classes = self.dash_layout_classes + classes if classes else []
            kwargs["className"] = f"{' '.join(all_classes)}" if all_classes else None
        kwargs_str = ", ".join(f"{name}={value}" for name, value in kwargs.items())
        return f"dcc.Markdown({kwargs_str})"

    @staticmethod
    def make_dash_component(path, component_id=None, classes=None):
        kwargs = {"children": f"load_dash_app('{path}', app=app"}
        if component_id:
            kwargs["id"] = component_id
        if classes:
            all_classes = self.dash_layout_classes + classes if classes else []
            kwargs["className"] = f"{' '.join(all_classes)}" if all_classes else None
        kwargs_str = ", ".join(f"{name}={value}" for name, value in kwargs.items())
        return f"html.Div({kwargs_str})"

    def blocks_to_components(self, blocks):
        """Convert blocks into Dash components"""
        for block in blocks:
            if block["type"] == self.markdown:
                content = self.preprocess_markdown(block["content"])
                yield self.make_markdown_component(content)
            else:
                # attrs.id       --> the ID
                # attrs.classes  --> list of classed
                # attrs.kvs      --> OrderedDict of key, val pairs
                attrs = PandocAttributes(block["attributes"], "markdown")
                if "dash" not in attrs.classes:
                    # Currently ignore code blocks without a `dash` class
                    continue

                if "app" in attrs.kvs:
                    # assume this is a file path.
                    # TODO: also support python imports with optional attribute:
                    # eg app.foo:layout
                    path = self.app_path / attrs["app"]
                else:
                    # TODO: support copying inline apps into new dir
                    continue
                component_id = attrs.id if attrs.id != "" else None
                classes = [c for c in attrs.classes if c not in ("dash", "app")]
                yield self.make_dash_component(
                    path, component_id=component_id, classes=classes
                )

    def parse_blocks(self, text):
        """Extract the code and non-code blocks from given markdown text.
        Returns a list of block dictionaries.
        Each dictionary has at least the keys 'type' and 'content',
        containing the type of the block ('markdown', 'code') and
        the contents of the block.
        Additional keys may be parsed as well.
        We should switch to an external markdown library if this
        gets much more complicated!
        """
        code_matches = [m for m in self.code_pattern.finditer(text)]

        # determine where the limits of the non code bits are
        # based on the code block edges
        text_starts = [0] + [m.end() for m in code_matches]
        text_stops = [m.start() for m in code_matches] + [len(text)]
        text_limits = list(zip(text_starts, text_stops))

        # list of the groups from the code blocks
        code_blocks = [self.new_code_block(**m.groupdict()) for m in code_matches]

        text_blocks = [self.new_text_block(content=text[i:j]) for i, j in text_limits]

        # create a list of the right length
        all_blocks = list(range(len(text_blocks) + len(code_blocks)))

        # NOTE: the behaviour here is a bit fragile in that we
        # assume that cells must alternate between code and
        # markdown. This isn't the case, as we could have
        # consecutive code cells, and we get around this by
        # stripping out empty cells. i.e. two consecutive code cells
        # have an empty markdown cell between them which is stripped
        # out because it is empty.

        # cells must alternate in order
        all_blocks[::2] = text_blocks
        all_blocks[1::2] = code_blocks

        # remove possible empty Markdown cells
        all_blocks = [
            b
            for b in all_blocks
            if not (b["type"] == self.markdown and not b["content"])
        ]
        return all_blocks

    def to_dash(self, string, blacken=True, **kwargs):
        blocks = self.parse_blocks(string)
        components = self.blocks_to_components(blocks)
        layout = f",\n{self.indent}".join(c for c in components)

        dash_app = f"""\
from dash import Dash, dcc, html
from balderdash import load_dash_app

app = Dash(__name__)
        
app.layout = html.Div(
    [
        {layout}
    ]
)
"""
        return format_str(dash_app, mode=FileMode())

    def converts(self, string, **kwargs):
        """Read string s to Dash file format."""
        return self.to_dash(string, **kwargs)

    def convert(self, fp, **kwargs):
        return self.to_dash(fp.read(), **kwargs)
