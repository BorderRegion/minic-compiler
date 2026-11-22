"""课堂验收与回归用例。运行 python3 -m unittest discover -s tests -v。"""

import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from compiler.common import MAX_INTEGER_DIGITS, MiniCError
from minic import compile_and_run


EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


class MiniCTests(unittest.TestCase):
    def test_examples(self):
        expected = {
            "arithmetic": ["a = 14", "b = 20", "difference = 6", "quotient = -3"],
            "branch": ["score = 75", "passed = true", "grade = 11", "safeAnd = false", "safeOr = true"],
            "loop": ["x = 3"],
        }
        for name, values in expected.items():
            with self.subTest(name=name):
                source = (EXAMPLES / (name + ".mc")).read_text(encoding="utf-8")
                reports = compile_and_run(source)
                self.assertEqual(list(reports), ["tokens", "ast", "symbols", "tac", "target", "result"])
                self.assertEqual(reports["result"], values)

    def test_loop_stage_output(self):
        source = (EXAMPLES / "loop.mc").read_text(encoding="utf-8")
        reports = compile_and_run(source)
        # README 中讲解的每一步都能在实际输出里找到。
        self.assertIn("2:10\tOP\t<", reports["tokens"])
        tree = "\n".join(reports["ast"])
        self.assertIn("  While\n    Binary <\n      Variable x\n      Literal 3\n    Block\n      Assign x", tree)
        self.assertIn("x\tint\t0\tx@0", reports["symbols"])
        tac = "\n".join(reports["tac"])
        self.assertIn("Label L1\n%t1 = x@0 < 3\nCjmp (%t1, L2, L3)\nLabel L2", tac)
        self.assertIn("Jmp L1\nLabel L3", tac)
        target = "\n".join(reports["target"])
        self.assertIn("LABEL L1\nLOAD x@0\nPUSH 3\nLT", target)
        self.assertIn("JTRUE L2\nJMP L3", target)

    def test_cli_reports_after_reruns(self):
        stages = ["tokens", "ast", "symbols", "tac", "target", "result"]
        cases = [
            ("int x = 7;", 0, 6),
            ("int x = 7;\nbool b = x;", 1, 3),
            ("int x = 1 / 0;", 1, 5),
            ("int x = ;", 1, 1),
            ("int x = @;", 1, 0),
            ("int x = 8;", 0, 6),
        ]
        with TemporaryDirectory() as directory:
            source = Path(directory) / "lesson.mc"
            output = Path(directory) / "lesson"
            output.mkdir()
            notes = output / "notes.txt"
            notes.write_text("课堂笔记", encoding="utf-8")
            command = [sys.executable, str(EXAMPLES.parent / "minic.py"), str(source), "--out", directory]
            for program, status, count in cases:
                with self.subTest(program=program):
                    source.write_text(program, encoding="utf-8")
                    run = subprocess.run(command, capture_output=True, text=True, check=False)
                    self.assertEqual(run.returncode, status)
                    self.assertNotIn("Traceback", run.stderr)
                    files = {p.stem for p in output.glob("*.txt")}
                    self.assertEqual(files, set(stages[:count]) | {"notes"})
                    self.assertEqual(notes.read_text(encoding="utf-8"), "课堂笔记")
                    if count == 3:
                        symbols = (output / "symbols.txt").read_text(encoding="utf-8")
                        self.assertIn("语义检查失败", symbols)
                        self.assertIn("x\tint\t0\tx@0", symbols)
                        self.assertIn("第 2 行，第 6 列", run.stderr)
                        self.assertIn(run.stderr.strip(), symbols)
            self.assertEqual((output / "result.txt").read_text(encoding="utf-8"), "x = 8\n")

    def test_operand_positions(self):
        # 同一变量在不同表达式中的 LOAD，均应指向实际读取处。
        cases = [
            ("int x;\nint y =\n    x;", 3, 5),
            ("int x;\nint y = x + 1;", 2, 9),
            ("int x;\nint y = 1 + x;", 2, 13),
            ("int x;\nint y = -x;", 2, 10),
            ("bool x;\nif (x) {}", 2, 5),
            ("bool x;\nwhile (x) {}", 2, 8),
            ("bool x;\nbool y = x && false;", 2, 10),
            ("bool x;\nbool y = false || x;", 2, 19),
        ]
        for source, line, column in cases:
            with self.subTest(source=source):
                with self.assertRaises(MiniCError) as error:
                    compile_and_run(source)
                self.assertEqual(str(error.exception), f"运行错误（第 {line} 行，第 {column} 列）：变量 x 尚未初始化")

    def test_input_limits(self):
        largest = "9" * MAX_INTEGER_DIGITS
        self.assertEqual(compile_and_run("int x = " + largest + ";")["result"], ["x = " + largest])
        cases = [
            ("int x = " + largest + "9;", "词法错误", "整数常量超过"),
            ("int x = " + largest + " + 1;", "运行错误", "整数运算结果超过"),
            ("int x = " + "(" * 2000 + "1" + ")" * 2000 + ";", "语法错误", "嵌套过深"),
            ("int x = " + "+".join(["1"] * 1500) + ";", "语法错误", "语法树超过"),
        ]
        for source, stage, reason in cases:
            with self.subTest(reason=reason):
                with self.assertRaises(MiniCError) as error:
                    compile_and_run(source)
                self.assertIn(stage, str(error.exception))
                self.assertIn(reason, str(error.exception))

    def test_control_flow(self):
        cases = [
            ("int x = 0; while (false) x = 1;", ["x = 0"]),
            ("int x = 0; if (true) if (false) x = 1; else x = 2;", ["x = 2"]),
            ("int x = 0; if (true) x = 1; else x = 2;", ["x = 1"]),
            ("int x = 3; { int x = 4; x = x + 1; }", ["x = 3"]),
            ("bool b = !(4 < 3) && (true == (3 != 2));", ["b = true"]),
            ("int x = 16 / 4 / 2 - 3 - 1;", ["x = -2"]),
            ("int i = 0; int x = 0; while (i < 2) { int j = 0; while (j < 3) { j = j + 1; x = x + 1; } i = i + 1; }", ["i = 2", "x = 6"]),
        ]
        for source, expected in cases:
            with self.subTest(source=source):
                self.assertEqual(compile_and_run(source)["result"], expected)

    def test_diagnostics(self):
        cases = [
            ("int x = @;", "词法错误（第 1 行，第 9 列）：非法字符"),
            ("int 1x;", "词法错误（第 1 行，第 5 列）：标识符不能以数字开头"),
            ("int x\nx = 1;", "语法错误（第 2 行，第 1 列）：此处需要 ';'"),
            ("int x = (1 + 2;", "语法错误（第 1 行，第 15 列）：此处需要 ')'"),
            ("int x = ;", "语法错误（第 1 行，第 9 列）：此处需要常量"),
            ("x = 1;", "语义错误（第 1 行，第 1 列）：变量 x 尚未声明"),
            ("int x; bool x;", "语义错误（第 1 行，第 13 列）：变量 x 在当前作用域重复声明"),
            ("bool x = 1;", "语义错误（第 1 行，第 6 列）：x 类型为 bool，赋值类型为 int"),
            ("while (1) {}", "语义错误（第 1 行，第 8 列）：条件表达式应为 bool"),
            ("{int y = 1;} int x = y;", "变量 y 尚未声明"),
            ("bool b = false && 1;", "&& 两侧都应为 bool"),
            ("int x = 1 / 0;", "运行错误（第 1 行，第 11 列）：除数为零"),
            ("bool b = false || (1/0 == 0);", "除数为零"),
            ("int i=0; while(i<2){int x; if(i==0)x=1; i=i+x;}", "变量 x 尚未初始化"),
        ]
        for source, message in cases:
            with self.subTest(source=source):
                with self.assertRaises(MiniCError) as error:
                    compile_and_run(source)
                self.assertIn(message, str(error.exception))


if __name__ == "__main__":
    unittest.main()
