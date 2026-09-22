"""Mechanical guards on the service-layer boundary.

The value of the extraction is that domain code can be called without a
request. That property is easy to lose one import at a time, so it is
checked here rather than left to review. See docs/service-layer.md.
"""
import ast
import re
import sys
from pathlib import Path

import pytest

API_SERVICE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(API_SERVICE_DIR))

DOMAIN_DIR = API_SERVICE_DIR / "domain"
DOMAIN_MODULES = sorted(DOMAIN_DIR.glob("*.py"))

# api_common is the HTTP adapter's toolbox and reads quart.session;
# quart itself would let session state back in through any door.
FORBIDDEN_IMPORTS = {"quart", "api_common"}


def imported_names(tree):
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name.split(".")[0]
        elif isinstance(node, ast.ImportFrom):
            if node.module and node.level == 0:
                yield node.module.split(".")[0]


@pytest.mark.parametrize("path", DOMAIN_MODULES, ids=lambda p: p.name)
def test_domain_module_does_not_import_the_http_layer(path):
    tree = ast.parse(path.read_text())
    offenders = FORBIDDEN_IMPORTS & set(imported_names(tree))
    assert not offenders, (
        f"{path.name} imports {sorted(offenders)}. Domain code must take "
        f"the acting user as an Actor argument instead of reading the "
        f"session; see docs/service-layer.md.")


#: A subscript of a bare name `session` -- not acad_session[:4] and not
#: db.session[...].
SESSION_READ = re.compile(r"(?<![\w.])session\s*\[")


@pytest.mark.parametrize("path", DOMAIN_MODULES, ids=lambda p: p.name)
def test_domain_module_never_touches_the_session(path):
    assert not SESSION_READ.search(path.read_text()), \
        f"{path.name} reads the Quart session directly."


@pytest.mark.parametrize("path", DOMAIN_MODULES, ids=lambda p: p.name)
def test_domain_functions_are_synchronous(path):
    tree = ast.parse(path.read_text())
    coroutines = [n.name for n in ast.walk(tree)
                  if isinstance(n, ast.AsyncFunctionDef)]
    assert not coroutines, (
        f"{path.name} defines async function(s) {coroutines}. Domain "
        f"functions stay synchronous so scripts and jobs can call them.")


def test_api_modules_do_not_import_each_others_privates():
    """The specific smell this phase set out to remove: api_reports and
    api_grades reaching into api_course_enrolment's name-mangled
    internals. Shared logic belongs in domain/."""
    offenders = []
    for path in sorted(API_SERVICE_DIR.glob("api_*.py")):
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom) or not node.module:
                continue
            if not node.module.startswith("api_"):
                continue
            for alias in node.names:
                if alias.name.startswith("_"):
                    offenders.append(f"{path.name}: {node.module}.{alias.name}")
    assert not offenders, "Private cross-module imports: " + ", ".join(offenders)
