"""MiniC 命令行入口，顺序调用五个编译阶段和虚拟机。"""

import argparse
import sys
from pathlib import Path

from compiler.codegen import generate_target
from compiler.common import MiniCError, format_tree
from compiler.ir import generate_ir
from compiler.lexer import scan
from compiler.parser import parse
from compiler.semantic import Analyzer
from compiler.vm import execute


REPORT_NAMES = ("tokens", "ast", "symbols", "tac", "target", "result")


def result_lines(symbols, memory):
    lines = []
    for symbol in symbols:
        if symbol.scope == 0:
            value = memory.get(symbol.storage, "<未初始化>")
            if isinstance(value, bool):
                value = "true" if value else "false"
            lines.append(f"{symbol.name} = {value}")
    return lines


def symbol_lines(symbols, error=None):
    status = "语义检查通过" if error is None else "语义检查失败"
    lines = [status, "名称\t类型\t作用域\t存储名"]
    for symbol in symbols:
        lines.append(f"{symbol.name}\t{symbol.type_name}\t{symbol.scope}\t{symbol.storage}")
    if error is not None:
        lines.append(str(error))
    return lines


def stage_reports(source):
    """每个阶段完成就交出结果，后续阶段出错时仍能查看前面的输出。"""
    tokens = scan(source)
    yield "tokens", [f"{t.line}:{t.column}\t{t.kind}\t{t.text}" for t in tokens]

    tree = parse(tokens)
    yield "ast", format_tree(tree)

    analyzer = Analyzer()
    try:
        symbols = analyzer.analyze(tree)
    except MiniCError as error:
        yield "symbols", symbol_lines(analyzer.symbols, error)
        raise
    yield "symbols", symbol_lines(symbols)

    tac = generate_ir(tree)
    yield "tac", [str(q) for q in tac]

    target = generate_target(tac)
    yield "target", [str(i) for i in target]

    memory = execute(target)
    yield "result", result_lines(symbols, memory)


def compile_and_run(source):
    return dict(stage_reports(source))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="MiniC 源文件")
    parser.add_argument("--out", type=Path, default=Path("output"), help="输出根目录")
    args = parser.parse_args()
    destination = args.out / args.source.stem
    try:
        source = args.source.read_text(encoding="utf-8")
        destination.mkdir(parents=True, exist_ok=True)
        # 只清理本工具的六个输出文件，保留同目录下的其他资料。
        for name in REPORT_NAMES:
            (destination / (name + ".txt")).unlink(missing_ok=True)
        for name, lines in stage_reports(source):
            content = "\n".join(lines) + "\n"
            (destination / (name + ".txt")).write_text(content, encoding="utf-8")
            print(f"\n[{name}]")
            print(content, end="")
    except (MiniCError, OSError, UnicodeError) as error:
        print(error, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
