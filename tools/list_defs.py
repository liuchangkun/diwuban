import os, sys, ast
from typing import List, Tuple

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
APP_DIR = os.path.join(ROOT, "app")

results: List[Tuple[str, List[Tuple[str, str, int, List[str]]]]] = []

for dirpath, _, filenames in os.walk(APP_DIR):
    for fn in filenames:
        if not fn.endswith(".py"):
            continue
        fpath = os.path.join(dirpath, fn)
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                src = f.read()
        except Exception as e:
            print(f"FILE: {fpath}\n  [ERROR] cannot read: {e}")
            continue
        try:
            tree = ast.parse(src, filename=fpath)
        except Exception as e:
            print(f"FILE: {fpath}\n  [ERROR] cannot parse: {e}")
            continue
        items: List[Tuple[str, str, int, List[str]]] = []

        def _arg_names(fn: ast.AST) -> List[str]:
            if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
                args = []
                if fn.args.posonlyargs:
                    args += [a.arg for a in fn.args.posonlyargs]
                if fn.args.args:
                    args += [a.arg for a in fn.args.args]
                if fn.args.vararg:
                    args.append("*" + fn.args.vararg.arg)
                if fn.args.kwonlyargs:
                    args += [a.arg for a in fn.args.kwonlyargs]
                if fn.args.kwarg:
                    args.append("**" + fn.args.kwarg.arg)
                return args
            return []

        class ClassVisitor(ast.NodeVisitor):
            def visit_ClassDef(self, node: ast.ClassDef):
                for b in node.body:
                    if isinstance(b, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        args = _arg_names(b)
                        # drop self/cls
                        if args and args[0] in {"self", "cls"}:
                            args = args[1:]
                        items.append(
                            ("method", f"{node.name}.{b.name}", b.lineno, args)
                        )
                self.generic_visit(node)

        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                items.append(("function", node.name, node.lineno, _arg_names(node)))

        ClassVisitor().visit(tree)
        results.append((fpath, sorted(items, key=lambda t: t[2])))

for fpath, items in sorted(results):
    print(f"FILE: {fpath}")
    if not items:
        print("  [NO_FUNCS]")
    for kind, name, ln, args in items:
        arglist = ", ".join(args)
        print(f"  {kind.upper()}: {name}({arglist}) (line {ln})")
