"""栈式虚拟机：执行目标指令，返回变量存储区。指令保留源码位置用于报错。"""

import operator

from .common import MAX_INTEGER_DIGITS, MiniCError


INTEGER_BOUND = 10 ** MAX_INTEGER_DIGITS


OPERATIONS = {
    "ADD": operator.add, "SUB": operator.sub, "MUL": operator.mul,
    "LT": operator.lt, "LE": operator.le, "GT": operator.gt, "GE": operator.ge,
    "EQ": operator.eq, "NE": operator.ne,
}
UNARY = {"NEG": operator.neg, "POS": operator.pos, "NOT": operator.not_}


def divide(left, right, token):
    if right == 0:
        raise MiniCError("运行", token, "除数为零")
    # 先对绝对值做整数除法再恢复符号，负数除法向零截断。
    quotient = abs(left) // abs(right)
    if (left < 0) != (right < 0):
        return -quotient
    return quotient


def execute(code):
    labels = {}
    for index, instruction in enumerate(code):
        if instruction.op == "LABEL":
            labels[instruction.argument] = index + 1

    stack = []
    memory = {}
    pc = 0
    while pc < len(code):
        instruction = code[pc]
        op = instruction.op
        arg = instruction.argument
        pc += 1
        if op == "PUSH":
            if arg in ("true", "false"):
                stack.append(arg == "true")
            else:
                stack.append(int(arg))
        elif op == "CLEAR":
            memory.pop(arg, None)
        elif op == "LOAD":
            if arg not in memory:
                name = arg.split("@")[0]
                raise MiniCError("运行", instruction.token, f"变量 {name} 尚未初始化")
            stack.append(memory[arg])
        elif op == "STORE":
            memory[arg] = stack.pop()
        elif op in OPERATIONS or op == "DIV":
            # 计算 7 - 2 时先压 7 再压 2，因此先弹出的 2 是右操作数。
            right = stack.pop()
            left = stack.pop()
            if op == "DIV":
                stack.append(divide(left, right, instruction.token))
            else:
                value = OPERATIONS[op](left, right)
                if abs(value) >= INTEGER_BOUND:
                    raise MiniCError("运行", instruction.token, f"整数运算结果超过 {MAX_INTEGER_DIGITS} 位")
                stack.append(value)
        elif op in UNARY:
            stack.append(UNARY[op](stack.pop()))
        elif op == "JTRUE":
            if stack.pop():
                pc = labels[arg]
        elif op == "JMP":
            pc = labels[arg]
        elif op != "LABEL":
            raise ValueError(f"未知目标指令 {op}")
    return memory
