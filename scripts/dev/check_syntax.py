import ast
import pathlib

p = pathlib.Path("app/core/config/loader.py")
s = p.read_text(encoding="utf-8")
print("paren counts: (", s.count("("), ")", s.count(")"))
try:
    ast.parse(s)
    print("AST OK")
except SyntaxError as e:
    print("SyntaxError:", e)
    line = e.lineno or 0
    start = max(1, line - 10)
    end = line + 10
    for i, l in enumerate(s.splitlines()[start - 1 : end], start):
        print(f"{i:04}: {l}")
