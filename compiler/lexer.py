"""词法分析：源文本 → 带行列号的 Token 序列。"""

from .common import MAX_INTEGER_DIGITS, MiniCError, Token


KEYWORDS = {"int", "bool", "if", "else", "while"}
DOUBLE_OPERATORS = {"<=", ">=", "==", "!=", "&&", "||"}


def scan(source):
    tokens = []
    lines = source.split("\n")
    for line_number, line in enumerate(lines, start=1):
        index = 0
        while index < len(line):
            start = index
            char = line[index]
            index += 1
            if char.isspace():
                continue
            if line.startswith("//", start):
                break
            if char.isalpha() or char == "_":
                while index < len(line) and (line[index].isalnum() or line[index] == "_"):
                    index += 1
                kind = "IDENT"
                if line[start:index] in KEYWORDS:
                    kind = "KEYWORD"
                elif line[start:index] in ("true", "false"):
                    kind = "BOOLEAN"
            elif char.isdecimal():
                while index < len(line) and line[index].isdecimal():
                    index += 1
                if index < len(line) and (line[index].isalpha() or line[index] == "_"):
                    raise MiniCError("词法", Token("", "", line_number, start + 1), "标识符不能以数字开头")
                if index - start > MAX_INTEGER_DIGITS:
                    position = Token("INTEGER", "", line_number, start + 1)
                    raise MiniCError("词法", position, f"整数常量超过 {MAX_INTEGER_DIGITS} 位")
                kind = "INTEGER"
            elif line[start:start + 2] in DOUBLE_OPERATORS:
                # 先识别 <= 等双字符运算符，否则会误拆成 < 和 =。
                index += 1
                kind = "OP"
            elif char in "+-*/<>=!":
                kind = "OP"
            elif char in "(){};":
                kind = "DELIMITER"
            else:
                raise MiniCError("词法", Token("", char, line_number, start + 1), f"非法字符 {char!r}")
            tokens.append(Token(kind, line[start:index], line_number, start + 1))
    tokens.append(Token("EOF", "", len(lines), len(lines[-1]) + 1))
    return tokens
