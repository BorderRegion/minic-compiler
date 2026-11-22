"""递归下降语法分析：Token 序列 → AST。每个解析函数消费自己的 Token。"""

from .common import MiniCError, Node


class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.index = 0

    def current(self):
        return self.tokens[self.index]

    def take(self):
        token = self.current()
        self.index += 1
        return token

    def expect(self, text):
        if self.current().text != text:
            raise MiniCError("语法", self.current(), f"此处需要 '{text}'")
        return self.take()

    def program(self):
        root = Node("Program", self.current())
        while self.current().kind != "EOF":
            root.children.append(self.statement())
        return root

    def statement(self):
        token = self.current()
        if token.text == "{":
            block = Node("Block", self.take())
            while self.current().text != "}":
                if self.current().kind == "EOF":
                    raise MiniCError("语法", self.current(), "语句块缺少 '}'")
                block.children.append(self.statement())
            self.take()
            return block
        if token.text in ("int", "bool"):
            type_name = self.take().text
            if self.current().kind != "IDENT":
                raise MiniCError("语法", self.current(), "声明需要变量名")
            name = self.take()
            node = Node("Declare", name, value=type_name + " " + name.text, declared_type=type_name)
            if self.current().text == "=":
                self.take()
                node.children.append(self.expression())
            self.expect(";")
            return node
        if token.kind == "IDENT":
            name = self.take()
            self.expect("=")
            value = self.expression()
            self.expect(";")
            return Node("Assign", name, [value], name.text)
        if token.text in ("if", "while"):
            self.take()
            self.expect("(")
            condition = self.expression()
            self.expect(")")
            body = self.statement()
            if token.text == "while":
                return Node("While", token, [condition, body])
            node = Node("If", token, [condition, body])
            # 递归先读完整的内层语句，else 自然归属最近的 if。
            if self.current().text == "else":
                self.take()
                node.children.append(self.statement())
            return node
        raise MiniCError("语法", token, "此处需要声明、赋值、条件、循环或语句块")

    def binary_level(self, read_operand, operators):
        # 同一级从左到右组合，例如 8 / 4 / 2 解析为 (8 / 4) / 2。
        left = read_operand()
        while self.current().text in operators:
            operator = self.take()
            right = read_operand()
            left = Node("Binary", operator, [left, right], operator.text)
        return left

    def expression(self):
        return self.binary_level(self.logical_and, ("||",))

    def logical_and(self):
        return self.binary_level(self.equality, ("&&",))

    def equality(self):
        return self.binary_level(self.comparison, ("==", "!="))

    def comparison(self):
        return self.binary_level(self.addition, ("<", ">", "<=", ">="))

    def addition(self):
        # 加减两边先读完整的乘除表达式，乘除的优先级由此得到保证。
        return self.binary_level(self.product, ("+", "-"))

    def product(self):
        return self.binary_level(self.unary, ("*", "/"))

    def unary(self):
        if self.current().text in ("!", "-", "+"):
            operator = self.take()
            return Node("Unary", operator, [self.unary()], operator.text)
        return self.primary()

    def primary(self):
        token = self.current()
        if token.kind == "INTEGER" or token.text in ("true", "false"):
            return Node("Literal", self.take(), value=token.text)
        if token.kind == "IDENT":
            return Node("Variable", self.take(), value=token.text)
        if token.text == "(":
            self.take()
            result = self.expression()
            self.expect(")")
            return result
        raise MiniCError("语法", token, "此处需要常量、变量或括号表达式")


def parse(tokens):
    parser = Parser(tokens)
    try:
        tree = parser.program()
    except RecursionError:
        raise MiniCError("语法", parser.current(), "嵌套过深，请拆分表达式或语句") from None

    # 很长的加减链也会构造深树，即使解析它时没有递归。
    # 在交给后续递归遍历之前，用显式栈统一检查树的深度。
    pending = [(tree, 1)]
    while pending:
        node, depth = pending.pop()
        if depth > 256:
            raise MiniCError("语法", node.token, "语法树超过 256 层，请拆分表达式或语句")
        for child in node.children:
            pending.append((child, depth + 1))
    return tree
