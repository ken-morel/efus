"""Efus parser class and functions."""
import re
from . import types
from decimal import Decimal
from typing import Optional


class Parser:
    idx: int
    text: str
    instructions: 2
    file: Optional[str]
    SPACE = frozenset(" \t")
    tag_def = re.compile(r"(?P<name>[\w]+)(?:\&(?P<alias>[\w]+))?")
    tag_name = re.compile(r"(?P<name>\w[\w\d\:]*)\=")
    decimal = re.compile(r"([+\-]?\d+(?:\.\d+)?)")
    integer = re.compile(r"([+\-]?\d+)")
    # string = re.compile(r"((\"|')[.+()]\1)")

    class End(Exception):
        pass

    class EOF(End):
        pass

    class EOL(End):
        pass

    class SyntaxError(SyntaxError):
        pass

    def __init__(self, file: str = None):
        self.idx = 0
        self.text = ""
        self.instructions = []
        self.parsed = []
        self.file = file

    def feed(self, text: str) -> tuple[types.EInstr]:
        """Feed code in parser."""
        self.text += text
        self.go_ahead()
        return self.instructions

    def go_ahead(self):
        while True:  # For each logical line
            try:
                indent = self.next_indent()
            except Parser.EOF:  # Getcha that next line!
                break
            tag = Parser.tag_def.search(self.text, self.idx)
            print(tag, self.idx)
            if tag and tag.span()[0] == self.idx:
                self.idx += tag.span()[1] - tag.span()[0]
                groups = tag.groupdict()
                attrs = self.parse_attrs()
                self.instructions.append(
                    (
                        indent,
                        types.TagDef(groups["name"], groups["alias"], attrs),
                    )
                )
            else:
                raise Exception()

    def parse_attrs(self) -> list[tuple]:
        attrs = []
        try:
            while True:
                attrs += self.parse_next_attr_value()
        except Parser.EOL:
            pass
        return attrs

    def parse_next_attr_value(self) -> list[tuple]:
        self.inline_spaces()
        name = Parser.tag_name.search(self.text, self.idx)
        if name is not None:
            self.idx += name.span()[1] - name.span()[0]
            val = self.parse_next_value()
            return [(name.groupdict()["name"], val)]
        else:
            return []

    def parse_next_value(self):
        if (m := Parser.decimal.search(self.text, self.idx)) and m.span()[
            0
        ] == self.idx:
            self.idx += m.span()[1] - m.span()[0]
            return types.ENumber(Decimal(m.groups()[0]))
        elif (m := Parser.integer.search(self.text, self.idx)) and m.span()[
            0
        ] == self.idx:
            self.idx += m.span()[1] - m.span()[0]
            return types.ENumber(int(m.groups()[0]))
        elif (b := self.text[self.idx]) in "'\"":
            begin = self.idx
            self.idx += 1
            while self.idx < len(self.text):
                if self.text[self.idx] == b:
                    self.idx += 1
                    break
                elif self.text[self.idx] == "\\":
                    self.idx += 2
                elif self.text[self.idx] == "\n":
                    raise Parser.SyntaxError("Untermated string before EOL")
                else:
                    self.idx += 1
            else:
                raise Parser.SyntaxError("Untermated string at EOF")
            return types.EStr(eval(self.text[begin : self.idx]))
        else:
            raise Parser.SyntaxError("Unknown literal\n" + self.py_stack())

    def inline_spaces(self):
        while self.idx < len(self.text):
            if self.text[self.idx] in Parser.SPACE:
                self.idx += 1
            elif self.text[self.idx] == "\n":
                raise Parser.EOL()
            else:
                break
        else:
            raise Parser.EOL()

    def next_indent(self) -> int:
        begin = self.idx
        while self.idx < len(self.text):
            if self.text[self.idx] in Parser.SPACE:
                self.idx += 1
            elif self.text[self.idx] == "\n":
                self.idx += 1
                begin = self.idx
            else:
                print("next indent closes at", self)
                break
        else:
            self.idx = begin
            raise Parser.EOF()
        return self.idx - begin

    def __repr__(self):
        begin = (
            self.text.rindex("\n", 0, self.idx) + 1
            if "\n" in self.text[: self.idx]
            else 0
        )
        end = (
            self.text.index("\n", self.idx)
            if "\n" in self.text[self.idx :]
            else len(self.text)
        )
        pos = self.idx - begin
        return "Parser: %s{\n  | %s\n  | %s^" % (
            self.instructions,
            self.text[begin:end],
            pos * " ",
        )

    def py_stack(self) -> str:
        """Create a python-like stack."""
        begin = (
            self.text.rindex("\n", 0, self.idx) + 1
            if "\n" in self.text[: self.idx]
            else 0
        )
        end = (
            self.text.index("\n", self.idx)
            if "\n" in self.text[self.idx :]
            else len(self.text)
        )
        pos = self.idx - begin
        ln = self.text[: self.idx].count("\n") + 1
        return '  File "%s", line %d, column %d\n  %s\n  %s^' % (
            self.file or "<string>",
            ln,
            pos,
            self.text[begin:end],
            pos * " ",
        )


def parse_file(path: str) -> types.Efus:
    with open(path) as f:
        return types.Efus(Parser(path).feed(f.read()))
