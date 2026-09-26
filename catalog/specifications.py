from dataclasses import dataclass, field
from html import escape

from django.utils.safestring import mark_safe


@dataclass
class SpecificationNode:
    text: str
    children: list["SpecificationNode"] = field(default_factory=list)


def _indentation_level(line):
    prefix_length = 0
    indentation_width = 0
    for character in line:
        if character == " ":
            prefix_length += 1
            indentation_width += 1
        elif character == "\t":
            prefix_length += 1
            indentation_width += 2
        else:
            break

    prefix = line[:prefix_length]
    is_child = "\t" in prefix or len(prefix) >= 2
    if not is_child:
        return 0, line

    return max(1, indentation_width // 2), line[prefix_length:]


def parse_specifications(value):
    """Parse indented specification text into an arbitrary-depth tree."""
    roots = []
    stack = []

    for original_line in (value or "").splitlines():
        if not original_line.strip():
            continue

        level, text = _indentation_level(original_line)
        node = SpecificationNode(text=text)

        if level == 0 or not roots:
            roots.append(node)
            stack = [(0, node)]
            continue

        while stack and stack[-1][0] >= level:
            stack.pop()

        if stack:
            stack[-1][1].children.append(node)
            stack.append((level, node))
        else:
            roots.append(node)
            stack = [(0, node)]

    return roots


def render_specification_list(nodes):
    """Render a parsed specification tree as escaped nested HTML lists."""
    if not nodes:
        return ""

    output = ['<ul class="spec-list">']
    events = [("close_root", None)]
    events.extend(("node", node) for node in reversed(nodes))

    while events:
        event, node = events.pop()
        if event == "node":
            output.append(f"<li>{escape(node.text, quote=True)}")
            if node.children:
                output.append("<ul>")
                events.append(("close_li", None))
                events.append(("close_ul", None))
                events.extend(
                    ("node", child) for child in reversed(node.children)
                )
            else:
                output.append("</li>")
        elif event == "close_ul":
            output.append("</ul>")
        elif event == "close_li":
            output.append("</li>")
        else:
            output.append("</ul>")

    return mark_safe("".join(output))
