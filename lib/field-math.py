#!/usr/bin/env python3
"""Field Math — Hostess 7 sovereign calculator backend (no sympy).

Pure stdlib Field compute: arithmetic, fractions, trig, stats, linear algebra,
and light algebra/calculus patterns. Replaces sympy on the Field plane.

  python3 lib/field-math.py "2+2"
  python3 lib/field-math.py "sqrt(16)"
  python3 lib/field-math.py "diff x**2"
"""
from __future__ import annotations

import ast
import cmath
import math
import operator
import re
import sys
from decimal import Decimal, getcontext
from fractions import Fraction
from typing import Any

IRONCLAD = "ironclad:field-math:1"
METHOD = "field"

getcontext().prec = 28

# ─── safe eval namespace ─────────────────────────────────────────────────────

def _sqrt(x: Any) -> Any:
    if isinstance(x, complex) or (isinstance(x, (int, float)) and x < 0):
        return cmath.sqrt(x)
    return math.sqrt(float(x))


def _log(x: Any, base: Any | None = None) -> float:
    if base is None:
        return math.log(float(x))
    return math.log(float(x), float(base))


def _abs(x: Any) -> Any:
    if isinstance(x, complex):
        return abs(x)
    return abs(x)


_FIELD_NS: dict[str, Any] = {
    "pi": math.pi,
    "e": math.e,
    "tau": math.tau,
    "inf": math.inf,
    "nan": math.nan,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "asin": math.asin,
    "acos": math.acos,
    "atan": math.atan,
    "atan2": math.atan2,
    "sinh": math.sinh,
    "cosh": math.cosh,
    "tanh": math.tanh,
    "sqrt": _sqrt,
    "log": _log,
    "ln": math.log,
    "log10": math.log10,
    "log2": math.log2,
    "exp": math.exp,
    "abs": _abs,
    "floor": math.floor,
    "ceil": math.ceil,
    "factorial": math.factorial,
    "degrees": math.degrees,
    "radians": math.radians,
    "hypot": math.hypot,
    "pow": pow,
    "min": min,
    "max": max,
    "round": round,
    # complex helpers
    "I": 1j,
    "i": 1j,
    "j": 1j,
    "real": lambda z: complex(z).real,
    "imag": lambda z: complex(z).imag,
    "conj": lambda z: complex(z).conjugate(),
}


_BINOPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_UNARY = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}


class FieldMathError(ValueError):
    pass


def _eval_ast(node: ast.AST, names: dict[str, Any] | None = None) -> Any:
    names = names or {}
    ns = {**_FIELD_NS, **names}
    if isinstance(node, ast.Expression):
        return _eval_ast(node.body, names)
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Name):
        if node.id in ns:
            return ns[node.id]
        raise FieldMathError(f"unknown_symbol:{node.id}")
    if isinstance(node, ast.BinOp):
        op = _BINOPS.get(type(node.op))
        if not op:
            raise FieldMathError(f"unsupported_binop:{type(node.op).__name__}")
        return op(_eval_ast(node.left, names), _eval_ast(node.right, names))
    if isinstance(node, ast.UnaryOp):
        op = _UNARY.get(type(node.op))
        if not op:
            raise FieldMathError(f"unsupported_unary:{type(node.op).__name__}")
        return op(_eval_ast(node.operand, names))
    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name):
            raise FieldMathError("only_named_calls")
        fn = ns.get(node.func.id)
        if not callable(fn):
            raise FieldMathError(f"unknown_function:{node.func.id}")
        args = [_eval_ast(a, names) for a in node.args]
        return fn(*args)
    if isinstance(node, ast.Tuple):
        return tuple(_eval_ast(e, names) for e in node.elts)
    if isinstance(node, ast.List):
        return [_eval_ast(e, names) for e in node.elts]
    raise FieldMathError(f"unsupported_ast:{type(node).__name__}")


def _preprocess(expr: str) -> str:
    s = (expr or "").strip()
    s = s.replace("^", "**").replace("×", "*").replace("÷", "/")
    s = s.replace("π", "pi")
    # 2i → 2*I , trailing bare i
    s = re.sub(r"(?<=\d)(?=[iIjJ]\b)", "*", s)
    s = re.sub(r"\bi\b", "I", s)
    s = re.sub(r"\bj\b", "I", s)
    # 2(3+4) → 2*(3+4)
    s = re.sub(r"(\d)\s*\(", r"\1*(", s)
    s = re.sub(r"\)\s*(\d)", r")*\1", s)
    s = re.sub(r"\)\s*\(", r")*(", s)
    return s


def field_eval(expr: str, *, names: dict[str, Any] | None = None) -> Any:
    """Evaluate a Field math expression safely (no builtins, no attributes)."""
    src = _preprocess(expr)
    if not src:
        raise FieldMathError("empty_expr")
    tree = ast.parse(src, mode="eval")
    for node in ast.walk(tree):
        if isinstance(node, (ast.Attribute, ast.Subscript, ast.Dict, ast.Set,
                             ast.Lambda, ast.ListComp, ast.GeneratorExp,
                             ast.Await, ast.Yield, ast.Import, ast.ImportFrom)):
            raise FieldMathError(f"forbidden_node:{type(node).__name__}")
    return _eval_ast(tree, names)


def format_field(val: Any) -> str:
    """Canonical Field result string."""
    if val is None:
        return ""
    if isinstance(val, (list, tuple)):
        return ",".join(format_field(v) for v in val)
    if isinstance(val, complex):
        if abs(val.imag) < 1e-12:
            return format_field(val.real)
        re_s = format_field(val.real)
        im = val.imag
        sign = "+" if im >= 0 else "-"
        im_s = format_field(abs(im))
        if im_s == "1":
            im_s = ""
        return f"{re_s}{sign}{im_s}I"
    if isinstance(val, bool):
        return "1" if val else "0"
    if isinstance(val, Fraction):
        if val.denominator == 1:
            return str(val.numerator)
        return f"{val.numerator}/{val.denominator}"
    if isinstance(val, Decimal):
        s = format(val.normalize(), "f")
        if "." in s:
            s = s.rstrip("0").rstrip(".")
        return s or "0"
    if isinstance(val, float):
        if math.isnan(val):
            return "nan"
        if math.isinf(val):
            return "inf" if val > 0 else "-inf"
        if abs(val - round(val)) < 1e-12:
            return str(int(round(val)))
        # try rational of small denom
        try:
            fr = Fraction(val).limit_denominator(10000)
            if abs(float(fr) - val) < 1e-9:
                return format_field(fr)
        except (ValueError, OverflowError):
            pass
        s = f"{val:.12g}"
        return s
    if isinstance(val, int):
        return str(val)
    s = str(val).replace("**", "^").replace("j", "I")
    return re.sub(r"\s+", "", s)


def results_match(got: str, expected: str) -> bool:
    got_n = re.sub(r"\s+", "", (got or "").lower())
    exp_n = re.sub(r"\s+", "", (expected or "").lower())
    if got_n == exp_n:
        return True
    if exp_n in got_n or got_n in exp_n:
        return True
    try:
        g = field_eval(got_n.replace("^", "**"))
        e = field_eval(exp_n.replace("^", "**"))
        if isinstance(g, (int, float)) and isinstance(e, (int, float)):
            return abs(float(g) - float(e)) < 1e-6
        if isinstance(g, complex) or isinstance(e, complex):
            return abs(complex(g) - complex(e)) < 1e-6
        return format_field(g) == format_field(e)
    except Exception:
        pass
    try:
        return abs(float(got_n) - float(exp_n)) < 1e-6
    except ValueError:
        return False


# ─── structured ops ──────────────────────────────────────────────────────────

def parse_vector(text: str) -> list[Any]:
    inside = re.search(r"\[([^\]]+)\]", text)
    raw = inside.group(1) if inside else text.strip()
    cells = [c.strip() for c in re.split(r"[,\s]+", raw) if c.strip()]
    return [field_eval(c) for c in cells]


def parse_matrix(text: str) -> list[list[Any]] | None:
    rows_raw = re.findall(r"\[([^\[\]]+)\]", text)
    if not rows_raw:
        return None
    rows: list[list[Any]] = []
    for row in rows_raw:
        cells = [c.strip() for c in re.split(r"[,\s]+", row.strip()) if c.strip()]
        if not cells:
            continue
        rows.append([field_eval(c) for c in cells])
    return rows or None


def matrix_det(mat: list[list[Any]]) -> Any:
    n = len(mat)
    if n == 0 or any(len(r) != n for r in mat):
        raise FieldMathError("matrix_not_square")
    if n == 1:
        return mat[0][0]
    if n == 2:
        return mat[0][0] * mat[1][1] - mat[0][1] * mat[1][0]
    # Laplace expansion
    total = 0
    for j in range(n):
        minor = [[mat[i][k] for k in range(n) if k != j] for i in range(1, n)]
        total += ((-1) ** j) * mat[0][j] * matrix_det(minor)
    return total


def matrix_eigenvals_2x2(mat: list[list[Any]]) -> list[Any]:
    if len(mat) != 2 or len(mat[0]) != 2:
        raise FieldMathError("eigen_2x2_only")
    a, b = float(mat[0][0]), float(mat[0][1])
    c, d = float(mat[1][0]), float(mat[1][1])
    tr = a + d
    det = a * d - b * c
    disc = tr * tr - 4 * det
    if disc >= 0:
        s = math.sqrt(disc)
        return [(tr + s) / 2, (tr - s) / 2]
    s = cmath.sqrt(disc)
    return [(tr + s) / 2, (tr - s) / 2]


def _poly_coeffs(expr: str, var: str = "x") -> list[float] | None:
    """Parse simple polynomial a*x**n + ... into coeffs high→low. Returns None if not poly."""
    src = _preprocess(expr)
    # replace var with placeholder for structure check
    try:
        tree = ast.parse(src, mode="eval")
    except SyntaxError:
        return None
    # Evaluate at several points and fit degree ≤4 via finite differences if only powers of var
    pts = [0, 1, 2, 3, 4, 5]
    vals = []
    for t in pts:
        try:
            vals.append(float(field_eval(src, names={var: t})))
        except Exception:
            return None
    # Newton divided differences for degree detection
    # For battery we mainly need constant/linear/quadratic/cubic monomials — use sympy-free power scan
    # Collect terms via regex for a*x**n + b*x + c style
    s = src.replace(" ", "")
    # expand (x+1)**2 style not supported here
    terms = re.split(r"(?=[+-])", s)
    coeffs: dict[int, float] = {}
    for term in terms:
        if not term or term in "+-":
            continue
        t = term
        sign = 1.0
        if t.startswith("+"):
            t = t[1:]
        if t.startswith("-"):
            sign = -1.0
            t = t[1:]
        if not t:
            continue
        # a*var**n
        m = re.fullmatch(rf"(?:(\d+(?:\.\d*)?)?\*)?{var}\*\*(\d+)", t)
        if m:
            a = float(m.group(1) or 1) * sign
            n = int(m.group(2))
            coeffs[n] = coeffs.get(n, 0.0) + a
            continue
        m = re.fullmatch(rf"(?:(\d+(?:\.\d*)?)?\*)?{var}", t)
        if m:
            a = float(m.group(1) or 1) * sign
            coeffs[1] = coeffs.get(1, 0.0) + a
            continue
        m = re.fullmatch(r"(\d+(?:\.\d*)?)", t)
        if m:
            coeffs[0] = coeffs.get(0, 0.0) + sign * float(m.group(1))
            continue
        # bare fraction or other — fail poly
        try:
            coeffs[0] = coeffs.get(0, 0.0) + sign * float(field_eval(t))
        except Exception:
            return None
    if not coeffs:
        return None
    deg = max(coeffs)
    return [coeffs.get(i, 0.0) for i in range(deg, -1, -1)]


def field_diff(expr: str, var: str = "x") -> str:
    """Differentiate polynomial (and simple powers) in Field."""
    coeffs = _poly_coeffs(expr, var)
    if coeffs is None:
        # try monomial a*var**n only via eval of difference quotient numeric + rationalize
        raise FieldMathError("diff_poly_only")
    # high → low degree
    deg = len(coeffs) - 1
    out: list[str] = []
    for i, a in enumerate(coeffs):
        power = deg - i
        if power == 0 or abs(a) < 1e-15:
            continue
        na = a * power
        npow = power - 1
        if abs(na) < 1e-15:
            continue
        if npow == 0:
            out.append(format_field(na))
        elif npow == 1:
            if abs(na - 1) < 1e-12:
                out.append(var)
            elif abs(na + 1) < 1e-12:
                out.append(f"-{var}")
            else:
                out.append(f"{format_field(na)}*{var}")
        else:
            if abs(na - 1) < 1e-12:
                out.append(f"{var}**{npow}")
            else:
                out.append(f"{format_field(na)}*{var}**{npow}")
    if not out:
        return "0"
    # join with + handling leading minus
    s = out[0]
    for t in out[1:]:
        if t.startswith("-"):
            s += t
        else:
            s += "+" + t
    return s.replace("**", "^")


def field_integrate(expr: str, var: str = "x") -> str:
    coeffs = _poly_coeffs(expr, var)
    if coeffs is None:
        raise FieldMathError("integrate_poly_only")
    deg = len(coeffs) - 1
    out: list[str] = []
    for i, a in enumerate(coeffs):
        power = deg - i
        if abs(a) < 1e-15:
            continue
        npow = power + 1
        na = a / npow
        if npow == 1:
            out.append(format_field(na) if abs(na - 1) > 1e-12 else var if abs(na - 1) < 1e-12 else f"{format_field(na)}*{var}")
            if abs(na - 1) < 1e-12:
                out[-1] = var
            elif abs(na + 1) < 1e-12:
                out[-1] = f"-{var}"
            else:
                out[-1] = f"{format_field(na)}*{var}"
        else:
            if abs(na - 1) < 1e-12:
                out.append(f"{var}**{npow}")
            else:
                out.append(f"{format_field(na)}*{var}**{npow}")
    if not out:
        return "C"
    s = out[0]
    for t in out[1:]:
        if t.startswith("-"):
            s += t
        else:
            s += "+" + t
    return s.replace("**", "^") + "+C"


def field_solve_linear_quadratic(expr: str, var: str = "x") -> list[Any]:
    """Solve poly = 0 for degree 1–2. expr may be 'lhs=rhs' or bare."""
    src = expr
    if "=" in src:
        lhs, rhs = src.split("=", 1)
        combined = f"({lhs})-({rhs})"
    else:
        combined = src
    coeffs = _poly_coeffs(combined, var)
    if coeffs is None:
        raise FieldMathError("solve_poly_only")
    # strip leading zeros
    while len(coeffs) > 1 and abs(coeffs[0]) < 1e-15:
        coeffs = coeffs[1:]
    if len(coeffs) == 1:
        if abs(coeffs[0]) < 1e-15:
            raise FieldMathError("identity")
        return []
    if len(coeffs) == 2:
        a, b = coeffs[0], coeffs[1]
        return [-b / a]
    if len(coeffs) == 3:
        a, b, c = coeffs[0], coeffs[1], coeffs[2]
        disc = b * b - 4 * a * c
        if disc >= 0:
            s = math.sqrt(disc)
            return [(-b + s) / (2 * a), (-b - s) / (2 * a)]
        s = cmath.sqrt(disc)
        return [(-b + s) / (2 * a), (-b - s) / (2 * a)]
    raise FieldMathError("solve_degree_le_2")


def fft_field(vals: list[complex]) -> list[complex]:
    n = len(vals)
    if n == 0:
        return []
    if n & (n - 1) == 0 and n >= 2:
        # Cooley–Tukey radix-2
        half = fft_field(vals[0::2]) + [0j]  # placeholder type
        # proper implementation:
        def _fft(a: list[complex]) -> list[complex]:
            m = len(a)
            if m == 1:
                return a
            even = _fft(a[0::2])
            odd = _fft(a[1::2])
            t = [cmath.exp(-2j * math.pi * k / m) * odd[k] for k in range(m // 2)]
            return [even[k] + t[k] for k in range(m // 2)] + [even[k] - t[k] for k in range(m // 2)]
        return _fft([complex(v) for v in vals])
    # DFT O(n^2)
    out = []
    for k in range(n):
        s = sum(vals[j] * cmath.exp(-2j * math.pi * k * j / n) for j in range(n))
        out.append(s)
    return out


def compute(text: str) -> dict[str, Any]:
    """Field compute — primary API for Hostess 7 calculator."""
    query = (text or "").strip()
    low = query.lower().strip()
    if not query:
        return {"ok": False, "error": "empty_query", "method": METHOD, "ironclad_cite": IRONCLAD}

    try:
        # Percent
        m = re.match(r"^(\d+(?:\.\d+)?)\s*%\s*of\s+(\d+(?:\.\d+)?)$", low)
        if m:
            pct = Decimal(m.group(1)) / Decimal(100)
            base = Decimal(m.group(2))
            result = pct * base
            return {
                "ok": True, "query": query, "result": format_field(result),
                "category": "arithmetic", "method": "field_decimal",
                "work": f"{m.group(1)}% × {m.group(2)}", "ironclad_cite": IRONCLAD,
            }

        # Mean
        m = re.match(r"^(?:mean|average)\s+(.+)$", low)
        if m:
            vals = parse_vector(m.group(1))
            result = sum(float(v) for v in vals) / len(vals)
            return {"ok": True, "query": query, "result": format_field(result),
                    "category": "statistics", "method": "field_mean", "ironclad_cite": IRONCLAD}

        # Std
        m = re.match(r"^std(?:dev)?\s+(.+)$", low)
        if m:
            vals = [float(v) for v in parse_vector(m.group(1))]
            mu = sum(vals) / len(vals)
            result = math.sqrt(sum((v - mu) ** 2 for v in vals) / len(vals))
            return {"ok": True, "query": query, "result": format_field(result),
                    "category": "statistics", "method": "field_std", "ironclad_cite": IRONCLAD}

        # FFT
        m = re.match(r"^fft\s+(.+)$", low)
        if m:
            vals = [complex(float(v) if not isinstance(v, complex) else v) for v in parse_vector(m.group(1))]
            spec = fft_field(vals)
            parts = []
            for c in spec:
                if abs(c.imag) < 1e-9:
                    parts.append(format_field(c.real))
                else:
                    parts.append(format_field(c))
            return {"ok": True, "query": query, "result": ",".join(parts),
                    "category": "technology", "method": "field_fft", "ironclad_cite": IRONCLAD}

        # Dot
        m = re.match(r"^dot\s+(.+?)\s+(.+)$", low)
        if m:
            a = parse_vector(m.group(1))
            b = parse_vector(m.group(2))
            result = sum(float(ai) * float(bi) for ai, bi in zip(a, b))
            return {"ok": True, "query": query, "result": format_field(result),
                    "category": "technology", "method": "field_dot", "ironclad_cite": IRONCLAD}

        # Det
        m = re.match(r"^(?:det|determinant)\s+(.+)$", low)
        if m:
            mat = parse_matrix(m.group(1))
            if mat is not None:
                return {"ok": True, "query": query, "result": format_field(matrix_det(mat)),
                        "category": "linear_algebra", "method": "field_det", "ironclad_cite": IRONCLAD}

        # Eigenvalues 2×2
        m = re.match(r"^eigenvalues?\s+(.+)$", low)
        if m:
            mat = parse_matrix(m.group(1))
            if mat is not None:
                ev = matrix_eigenvals_2x2(mat)
                return {"ok": True, "query": query, "result": ",".join(format_field(k) for k in ev),
                        "category": "linear_algebra", "method": "field_eigen", "ironclad_cite": IRONCLAD}

        # Solve
        m = re.match(r"^solve\s+(.+)$", low)
        if m:
            sol = field_solve_linear_quadratic(m.group(1))
            return {"ok": True, "query": query, "result": format_field(sol),
                    "category": "algebra", "method": "field_solve", "ironclad_cite": IRONCLAD}

        # Diff
        m = re.match(r"^(?:diff|differentiate|derivative of)\s+(.+?)(?:\s+w\.?r\.?t\.?\s+(\w+))?$", low)
        if m:
            var = m.group(2) or "x"
            expr_s = m.group(1).strip()
            # strip "diff " if double
            result = field_diff(expr_s, var)
            return {"ok": True, "query": query, "result": result,
                    "category": "calculus", "method": "field_diff", "ironclad_cite": IRONCLAD}

        # Integrate definite
        m = re.match(r"^integrate\s+(.+?)\s+from\s+(.+?)\s+to\s+(.+)$", low)
        if m:
            # F(b)-F(a) via antiderivative poly
            anti = field_integrate(m.group(1), "x").replace("+C", "")
            a = field_eval(m.group(2))
            b = field_eval(m.group(3))
            # evaluate anti at a,b — replace x
            def _eval_anti(expr: str, xval: Any) -> Any:
                return field_eval(expr.replace("^", "**"), names={"x": xval})
            result = _eval_anti(anti, b) - _eval_anti(anti, a)
            return {"ok": True, "query": query, "result": format_field(result),
                    "category": "calculus", "method": "field_integrate_definite", "ironclad_cite": IRONCLAD}

        m = re.match(r"^(?:integrate|integral of)\s+(.+)$", low)
        if m:
            result = field_integrate(m.group(1), "x")
            return {"ok": True, "query": query, "result": result,
                    "category": "calculus", "method": "field_integrate", "ironclad_cite": IRONCLAD}

        # Factor / expand / simplify — Field: eval-normalize for numeric; poly identity for light cases
        for verb in ("factor", "expand", "simplify"):
            m = re.match(rf"^{verb}\s+(.+)$", low)
            if m:
                val = field_eval(m.group(1))
                return {"ok": True, "query": query, "result": format_field(val),
                        "category": "algebra", "method": f"field_{verb}", "ironclad_cite": IRONCLAD}

        # abs(...)
        m = re.match(r"^abs\s*\(\s*(.+?)\s*\)$", low)
        if m:
            val = field_eval(m.group(1))
            return {"ok": True, "query": query, "result": format_field(_abs(val)),
                    "category": "complex" if isinstance(val, complex) else "arithmetic",
                    "method": "field_abs", "ironclad_cite": IRONCLAD}

        # General expression
        val = field_eval(query)
        cat = "complex" if isinstance(val, complex) else "arithmetic"
        if any(fn in low for fn in ("sin", "cos", "tan", "asin", "acos", "atan")):
            cat = "trigonometry"
        return {
            "ok": True,
            "query": query,
            "result": format_field(val),
            "category": cat,
            "method": METHOD,
            "ironclad_cite": IRONCLAD,
            "engine": "field-math",
        }
    except Exception as exc:
        return {
            "ok": False,
            "query": query,
            "error": str(exc)[:240],
            "method": METHOD,
            "ironclad_cite": IRONCLAD,
        }


def ready() -> bool:
    """Field math is always ready — pure stdlib."""
    return True


def main() -> int:
    expr = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "2+2"
    import json
    print(json.dumps(compute(expr), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
