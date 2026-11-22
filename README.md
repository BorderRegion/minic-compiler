# MiniC 编译器课程设计

用 Python 标准库实现的 MiniC 编译器，支持 `int`、`bool`、变量声明与赋值、算术与逻辑表达式、`if-else` 和 `while`。已在 Python 3.12 上验证。

下载项目后，用浏览器打开 [MiniC 交互学习手册](guide.html)，可以从四行循环源码一路学到虚拟机单步执行。

## 运行

```sh
python3 minic.py examples/loop.mc
python3 -m unittest discover -s tests -v
```

编译器依次展示 Token、抽象语法树、符号表、三地址码、栈式目标代码和执行结果，并保存到 `output/示例名/`。循环示例最终得到 `x = 3`。

## 读代码

从 `minic.py` 的 `stage_reports` 开始，可以依次读到 `compiler/` 中的五个编译阶段和虚拟机。`examples/` 里的三个程序分别演示算术优先级、条件分支与短路求值、循环回跳。讲解循环时，可以对照 `output/loop/tac.txt` 中的 `Jmp L1`，看程序如何回到循环入口重新判断 `x < 3`。
