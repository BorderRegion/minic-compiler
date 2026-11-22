"""中间代码生成：已通过语义检查的 AST → 顺序排列的三地址码（TAC）。"""

from dataclasses import dataclass

from .common import Token


@dataclass
class Quad:
    op: str
    result: str
    first: str
    second: str
    token: Token
    operand_tokens: tuple = ()

    def operand_token(self, index):
        # 赋值和跳转直接记录所读表达式的位置；运算指令还区分左右操作数。
        if self.operand_tokens:
            return self.operand_tokens[index]
        return self.token

    def __str__(self):
        if self.op in ("Label", "Jmp"):
            return f"{self.op} {self.result}"
        if self.op == "Cjmp":
            return f"Cjmp ({self.first}, {self.result}, {self.second})"
        if self.op == "=":
            return f"{self.result} = {self.first}"
        if self.second:
            return f"{self.result} = {self.first} {self.op} {self.second}"
        return f"{self.result} = {self.op} {self.first}"


class Generator:
    def __init__(self):
        self.code = []
        self.temps = 0
        self.labels = 0

    def temporary(self):
        self.temps += 1
        return f"%t{self.temps}"

    def label(self):
        self.labels += 1
        return f"L{self.labels}"

    def emit(self, node, op, result, first="", second="", operands=()):
        tokens = tuple(child.token for child in operands)
        self.code.append(Quad(op, result, first, second, node.token, tokens))

    def expression(self, node):
        if node.kind == "Literal":
            return node.value
        if node.kind == "Variable":
            return node.storage
        if node.value in ("&&", "||"):
            return self.short_circuit(node)
        left = self.expression(node.children[0])
        right = ""
        if node.kind == "Binary":
            right = self.expression(node.children[1])
        result = self.temporary()
        self.emit(node, node.value, result, left, right, node.children)
        return result

    def short_circuit(self, node):
        # 左值已经决定结果时直接跳到末尾，跳过右侧的整段计算。
        result = self.temporary()
        evaluate_right = self.label()
        end = self.label()
        left = self.expression(node.children[0])
        self.emit(node.children[0], "=", result, left)
        if node.value == "&&":
            self.emit(node, "Cjmp", evaluate_right, result, end)
        else:
            self.emit(node, "Cjmp", end, result, evaluate_right)
        self.emit(node, "Label", evaluate_right)
        right = self.expression(node.children[1])
        self.emit(node.children[1], "=", result, right)
        self.emit(node, "Label", end)
        return result

    def statement(self, node):
        if node.kind in ("Program", "Block"):
            for child in node.children:
                self.statement(child)
        elif node.kind in ("Declare", "Assign"):
            if node.kind == "Declare":
                # 每次进入声明处都重新创建变量，循环中的局部量不会继承上轮的值。
                self.emit(node, "=", node.storage, "<未初始化>")
            if node.children:
                value = self.expression(node.children[0])
                self.emit(node.children[0], "=", node.storage, value)
        elif node.kind == "If":
            self.if_statement(node)
        elif node.kind == "While":
            self.while_statement(node)

    def if_statement(self, node):
        then = self.label()
        end = self.label()
        otherwise = end
        if len(node.children) == 3:
            otherwise = self.label()
        test = self.expression(node.children[0])
        self.emit(node.children[0], "Cjmp", then, test, otherwise)
        self.emit(node, "Label", then)
        self.statement(node.children[1])
        if otherwise != end:
            self.emit(node, "Jmp", end)
            self.emit(node, "Label", otherwise)
            self.statement(node.children[2])
        self.emit(node, "Label", end)

    def while_statement(self, node):
        start = self.label()
        body = self.label()
        end = self.label()
        self.emit(node, "Label", start)
        test = self.expression(node.children[0])
        self.emit(node.children[0], "Cjmp", body, test, end)
        self.emit(node, "Label", body)
        self.statement(node.children[1])
        # 循环体可能修改 x，因此回到条件计算处重新求 x < 3。
        self.emit(node, "Jmp", start)
        self.emit(node, "Label", end)


def generate_ir(tree):
    generator = Generator()
    generator.statement(tree)
    return generator.code
