import ast
from pathlib import Path


def test_dependency_direction():
    for layer in ["domain", "application"]:
        for path in Path("cashflow", layer).glob("*.py"):
            tree = ast.parse(path.read_text())
            for node in ast.walk(tree):
                names = (
                    [a.name for a in node.names]
                    if isinstance(node, ast.Import)
                    else [node.module or ""]
                    if isinstance(node, ast.ImportFrom)
                    else []
                )
                for name in names:
                    assert not name.startswith(
                        (
                            "fastapi",
                            "httpx",
                            "sqlite3",
                            "cashflow.infrastructure",
                            "cashflow.presentation",
                            "cashflow.main",
                        )
                    )
                    if layer == "domain":
                        assert not name.startswith("cashflow.application")
