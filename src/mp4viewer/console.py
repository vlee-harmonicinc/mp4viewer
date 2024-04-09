""" Console renderer """

import sys

from mp4viewer.tree import Tree


def _write(s):
    sys.stdout.write(s)


class ConsoleRenderer:
    """Print the box layout as a tree on to the console"""

    VERT = "!"
    HORI = "-"
    COLOR_HEADER = "\033[31m"  # red
    COLOR_ATTR = "\033[36m"  # cyan
    COLOR_SUB_TEXT = "\033[38;5;243m"  # gray
    ENDCOL = "\033[0m"

    def __init__(self, args, offset=None, indent_unit="    "):
        self.offset = "" if offset is None else offset
        self.indent_unit = indent_unit
        self.header_prefix = "`" + indent_unit.replace(" ", ConsoleRenderer.HORI)[1:]
        self.use_colors = True
        self.eol = "\n"
        self.indent_with_vert = self.indent_unit[:-1] + ConsoleRenderer.VERT
        self.args = args
        if args.latex:
            self._enable_latex_md_for_github()

    def _enable_latex_md_for_github(self):
        self.offset = self.offset.replace(" ", "&nbsp;")
        self.indent_unit = self.indent_unit.replace(" ", "&nbsp;")
        self.header_prefix = "\\`" + self.header_prefix[1:]
        self.eol = "  \n"
        self.indent_with_vert = self.indent_unit[: -len("&nbsp;")] + ConsoleRenderer.VERT
        ConsoleRenderer.COLOR_HEADER = " ${\\textsf{\\color{red}"
        ConsoleRenderer.COLOR_ATTR = " ${\\textsf{\\color{blue}"
        ConsoleRenderer.COLOR_SUB_TEXT = " ${\\textsf{\\color{grey}"
        ConsoleRenderer.ENDCOL = "}}$"

    def _wrap_color(self, text, color):
        suffix = ConsoleRenderer.ENDCOL if self.use_colors else ""
        return f"{color}{text}{suffix}"

    def _sub_text(self, text):
        if self.use_colors:
            wrapped_text = self._wrap_color(text, ConsoleRenderer.COLOR_SUB_TEXT)
        else:
            wrapped_text = f"<{text}>"
        return wrapped_text

    def _get_attr_color(self):
        return ConsoleRenderer.COLOR_ATTR if self.use_colors else ""

    def _get_data_prefix(self, atom, prefix):
        if atom.number_of_child_boxes():
            data_prefix = prefix + self.indent_with_vert + self.indent_unit
        else:
            data_prefix = prefix + self.indent_unit + self.indent_unit
        return data_prefix

    def _show_attr_list(self, atom, attr, prefix):
        items = attr.children
        truncated = self.args.truncate and len(items) > 10
        if truncated:
            items = items[:10]

        for child in items:
            self.show_node(child, prefix + self.indent_unit)

        if truncated:
            data_prefix = self._get_data_prefix(atom, prefix)
            msg = f"<<truncated {len(attr.children)-len(items)} items; rerun with -e to view them>>"
            text = self._wrap_color(msg, self._get_attr_color())
            _write(f"{data_prefix}{text}{self.eol}")

    def _show_attr(self, atom, attr, prefix):
        attr_color = self._get_attr_color()
        data_prefix = self._get_data_prefix(atom, prefix)
        _write(f"{data_prefix}{self._wrap_color(attr.name, attr_color)}: {attr.value}")
        if attr.display_value is not None:
            _write(f" {self._sub_text(attr.display_value)}{self.eol}")
        else:
            _write(self.eol)

    def show_node(self, node, prefix):
        """recursively display the node"""
        if node.is_atom():
            header_color = ConsoleRenderer.COLOR_HEADER if self.use_colors else ""
            header_prefix = prefix + self.header_prefix if len(prefix) else ""
        else:
            header_color = ""
            header_prefix = prefix + self.indent_unit
        _write(
            f"{header_prefix}{self._wrap_color(node.name, header_color)}"
            f" {self._sub_text(node.value) if node.value else ''}{self.eol}"
        )
        for i, child in enumerate(node.children):
            if child.is_attr():
                self._show_attr(node, child, prefix)
            elif child.is_list():
                self._show_attr_list(node, child, prefix)
            elif child.is_atom():
                child_indent = prefix + self.indent_with_vert
                if i + 1 == len(node.children):
                    child_indent = prefix + self.indent_unit
                self.show_node(child, child_indent)
            else:
                child_indent = prefix + self.indent_unit
                self.show_node(child, child_indent)

    def render(self, tree: Tree):
        """Render the tree"""
        print("=" * 80)
        self.show_node(tree, self.offset)

    def update_colors(self):
        """disable colours if they are not supported"""
        if not sys.stdout.isatty():
            self.disable_colors()

    def disable_colors(self):
        """Do not use ascii color prefixes and sufixes in the output"""
        self.use_colors = False
