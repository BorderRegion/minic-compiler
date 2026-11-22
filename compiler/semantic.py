"""语义分析：检查 AST，为变量绑定存储位置，返回按声明顺序排列的符号表。"""

from dataclasses import dataclass

from .common import MiniCError


@dataclass
class Symbol:
    name: str
    type_name: str
    scope: int
    storage: str


class Analyzer:
    def __init__(self):
        self.scopes = [{}]
        self.scope_ids = [0]
        self.next_scope = 1
        self.symbols = []

    def analyze(self, tree):
        self.statement(tree)
        return self.symbols

    def resolve(self, node):
        # 从内向外寻找，第一个匹配项就是当前位置可见的声明。
        for scope in reversed(self.scopes):
            if node.token.text in scope:
                symbol = scope[node.token.text]
                node.storage = symbol.storage
                return symbol
        raise MiniCError("语义", node.token, f"变量 {node.token.text} 尚未声明")

    def expression_type(self, node):
        if node.kind == "Literal":
            if node.value in ("true", "false"):
                return "bool"
            return "int"
        if node.kind == "Variable":
            return self.resolve(node).type_name

        operator = node.value
        left = self.expression_type(node.children[0])
        required = "int"
        if operator in ("!", "&&", "||"):
            required = "bool"
        if node.kind == "Unary":
            if left != required:
                raise MiniCError("语义", node.token, f"{operator} 的操作数应为 {required}")
            return required

        right = self.expression_type(node.children[1])
        if operator in ("==", "!="):
            if left != right:
                raise MiniCError("语义", node.token, "相等比较两侧的类型必须相同")
            return "bool"
        if left != required or right != required:
            raise MiniCError("语义", node.token, f"{operator} 两侧都应为 {required}")
        if operator in ("+", "-", "*", "/"):
            return "int"
        return "bool"

    def scoped_statements(self, statements):
        self.scopes.append({})
        self.scope_ids.append(self.next_scope)
        self.next_scope += 1
        for statement in statements:
            self.statement(statement)
        self.scopes.pop()
        self.scope_ids.pop()

    def statement(self, node):
        if node.kind == "Program":
            for child in node.children:
                self.statement(child)
        elif node.kind == "Block":
            self.scoped_statements(node.children)
        elif node.kind == "Declare":
            name = node.token.text
            if name in self.scopes[-1]:
                raise MiniCError("语义", node.token, f"变量 {name} 在当前作用域重复声明")
            scope = self.scope_ids[-1]
            node.storage = f"{name}@{scope}"
            symbol = Symbol(name, node.declared_type, scope, node.storage)
            self.scopes[-1][name] = symbol
            self.symbols.append(symbol)
            if node.children:
                self.check_assignment(node, symbol)
        elif node.kind == "Assign":
            self.check_assignment(node, self.resolve(node))
        else:
            if self.expression_type(node.children[0]) != "bool":
                raise MiniCError("语义", node.children[0].token, "条件表达式应为 bool")
            for body in node.children[1:]:
                if body.kind == "Block":
                    self.statement(body)
                else:
                    self.scoped_statements([body])

    def check_assignment(self, node, symbol):
        actual = self.expression_type(node.children[0])
        if actual != symbol.type_name:
            raise MiniCError("语义", node.token, f"{symbol.name} 类型为 {symbol.type_name}，赋值类型为 {actual}")


def analyze(tree):
    return Analyzer().analyze(tree)
