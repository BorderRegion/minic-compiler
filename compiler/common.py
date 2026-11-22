"""各阶段共用的 Token、语法树节点和错误位置。"""

import sys
from dataclasses import dataclass, field


# 十进制常量、运算结果和展示文件使用同一范围。
MAX_INTEGER_DIGITS = 4300
if hasattr(sys, "get_int_max_str_digits"):
    host_limit = sys.get_int_max_str_digits()
    if host_limit:
        MAX_INTEGER_DIGITS = min(MAX_INTEGER_DIGITS, host_limit)



class MiniCError(Exception):
    def __init__(self, stage, token, reason):
        super().__init__(f"{stage}错误（第 {token.line} 行，第 {token.column} 列）：{reason}")


@dataclass
class Token:
    kind: str
    text: str
    line: int
    column: int


@dataclass
class Node:
    """token 标记本节点的关键位置，例如运算符、声明名或 while。"""
    kind: str
    token: Token
    children: list = field(default_factory=list)
    value: str = ""
    # 语义分析填入唯一存储名，使后端能区分不同作用域里的同名变量。
    storage: str = ""
    declared_type: str = ""


def format_tree(node, depth=0):
    label = node.kind
    if node.value:
        label += " " + node.value
    lines = ["  " * depth + label]
    for child in node.children:
        lines.extend(format_tree(child, depth + 1))
    return lines
