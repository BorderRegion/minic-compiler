"""目标代码生成：把 TAC 操作数送上栈，运算后将栈顶写回目标位置。"""

from dataclasses import dataclass

from .common import Token


@dataclass
class Instruction:
    op: str
    argument: str
    token: Token

    def __str__(self):
        return (self.op + " " + self.argument).rstrip()


BINARY = {
    "+": "ADD", "-": "SUB", "*": "MUL", "/": "DIV",
    "<": "LT", "<=": "LE", ">": "GT", ">=": "GE", "==": "EQ", "!=": "NE",
}
UNARY = {"+": "POS", "-": "NEG", "!": "NOT"}


def operand_instruction(value, token):
    if value in ("true", "false") or value.isdecimal():
        return Instruction("PUSH", value, token)
    return Instruction("LOAD", value, token)


def generate_target(quads):
    code = []
    for q in quads:
        if q.op == "Label":
            code.append(Instruction("LABEL", q.result, q.token))
        elif q.op == "Jmp":
            code.append(Instruction("JMP", q.result, q.token))
        elif q.op == "Cjmp":
            code.append(operand_instruction(q.first, q.operand_token(0)))
            code.append(Instruction("JTRUE", q.result, q.token))
            code.append(Instruction("JMP", q.second, q.token))
        elif q.first == "<未初始化>":
            code.append(Instruction("CLEAR", q.result, q.token))
        else:
            code.append(operand_instruction(q.first, q.operand_token(0)))
            if q.second:
                code.append(operand_instruction(q.second, q.operand_token(1)))
                code.append(Instruction(BINARY[q.op], "", q.token))
            elif q.op != "=":
                code.append(Instruction(UNARY[q.op], "", q.token))
            code.append(Instruction("STORE", q.result, q.token))
    return code
