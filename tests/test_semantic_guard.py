"""
Unit and integration tests for semantic-merge-guard.
"""

import pytest
from pathlib import Path
from semantic_merge_guard.core import SemanticMergeGuard, FuncDef, FuncCall, RouteDef
from semantic_merge_guard.monetization import LicenseManager
from semantic_merge_guard.cli import main

def test_license_manager():
    comm = LicenseManager.get_tier(None)
    assert comm["tier"] == "community"

    ent = LicenseManager.get_tier("ord_ent_merge_safe")
    assert ent["tier"] == "enterprise"

    banner = LicenseManager.get_banner("semantic-merge-guard")
    assert "GABFQIK63R2NETJM7T673EAMZN4RJLLGP3OFUEJU5ZVTGWUKULZJNL6" in banner

def test_python_arity_mismatch(tmp_path):
    guard = SemanticMergeGuard()

    # File 1: Definition requires 3 args
    f1 = str(tmp_path / "calc.py")
    guard.scan_file(f1, """
def calculate_tax(amount, rate, country_code):
    return amount * rate
""")

    # File 2: Call only passes 2 args
    f2 = str(tmp_path / "billing.py")
    guard.scan_file(f2, """
def generate_bill():
    return calculate_tax(100.0, 0.15)
""")

    conflicts = guard.analyze_conflicts()
    assert len(conflicts) == 1
    assert conflicts[0].kind == "ARITY_MISMATCH"
    assert conflicts[0].severity == "CRITICAL"
    assert "calculate_tax" in conflicts[0].target_name

def test_duplicate_route_detection(tmp_path):
    guard = SemanticMergeGuard()

    f1 = str(tmp_path / "user_routes.py")
    guard.scan_file(f1, """
@app.get("/api/v1/users")
def get_users():
    return []
""")

    f2 = str(tmp_path / "admin_routes.py")
    guard.scan_file(f2, """
@app.get("/api/v1/users")
def list_users_admin():
    return []
""")

    conflicts = guard.analyze_conflicts()
    assert len(conflicts) == 1
    assert conflicts[0].kind == "DUPLICATE_ROUTE"
    assert "GET /api/v1/users" in conflicts[0].target_name

def test_ts_arity_and_routes(tmp_path):
    guard = SemanticMergeGuard()

    f1 = str(tmp_path / "api.ts")
    guard.scan_file(f1, """
export function processPayment(amount: number, currency: string, idempotencyKey: string) {
    return true;
}
router.post('/checkout', (req, res) => {});
""")

    f2 = str(tmp_path / "checkout.ts")
    guard.scan_file(f2, """
function checkout() {
    processPayment(50, 'USD');
}
router.post('/checkout', (req, res) => {});
""")

    conflicts = guard.analyze_conflicts()
    kinds = [c.kind for c in conflicts]
    assert "DUPLICATE_ROUTE" in kinds
    assert "ARITY_MISMATCH" in kinds

def test_variadic_and_zero_arg_functions(tmp_path):
    guard = SemanticMergeGuard()

    # 1. 0-arg function called with extra args -> SHOULD FAIL
    f1 = str(tmp_path / "zero.py")
    guard.scan_file(f1, "def stop_server(): pass\n")
    f2 = str(tmp_path / "caller.py")
    guard.scan_file(f2, "def invoke(): stop_server('immediate', True)\n")

    # 2. Variadic function called with multiple args -> SHOULD PASS
    f3 = str(tmp_path / "var.py")
    guard.scan_file(f3, "def custom_logger(msg, *args, **kwargs): pass\n")
    f4 = str(tmp_path / "log_call.py")
    guard.scan_file(f4, "def emit(): custom_logger('hello', 1, 2, 3, debug=True)\n")

    conflicts = guard.analyze_conflicts()
    # Only stop_server should be flagged
    assert len(conflicts) == 1
    assert conflicts[0].target_name == "stop_server"
    assert conflicts[0].kind == "ARITY_MISMATCH"


def test_cli_execution(tmp_path):
    # Test on empty clean dir
    clean_dir = tmp_path / "clean_repo"
    clean_dir.mkdir()
    (clean_dir / "app.py").write_text("def ping(): return 'pong'\nping()\n", encoding="utf-8")

    exit_code = main(["check", "--path", str(clean_dir)])
    assert exit_code == 0

    exit_code_lic = main(["license"])
    assert exit_code_lic == 0
