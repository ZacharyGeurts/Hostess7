#!/usr/bin/env python3
"""Field Array — numpy-free array plane for Hostess 7 Field stack.

Stdlib-only: list-backed arrays, FFT, convolve, stats. Prefer this over numpy
on the Field plane. Modules may soft-import field-array first, then numpy.

  from field_array import array, zeros, ones, fft, convolve, mean, max as amax
"""
from __future__ import annotations

import cmath
import math
import random
import struct
from typing import Any, Iterable, Iterator, Sequence

IRONCLAD = "ironclad:field-array:1"


class FArray:
    """Minimal ndarray-like for Field compute."""

    __slots__ = ("_data", "dtype", "shape")

    def __init__(self, data: Iterable[Any], dtype: str = "float64"):
        self.dtype = dtype
        items = list(data)
        if dtype in ("complex64", "complex128", "complex"):
            self._data = [complex(x) for x in items]
        elif dtype in ("int8", "int16", "int32", "int64", "uint8"):
            self._data = [int(x) for x in items]
        else:
            self._data = [float(x) for x in items]
        self.shape = (len(self._data),)

    def __len__(self) -> int:
        return len(self._data)

    def __iter__(self) -> Iterator[Any]:
        return iter(self._data)

    def __getitem__(self, idx: Any) -> Any:
        if isinstance(idx, slice):
            return FArray(self._data[idx], dtype=self.dtype)
        return self._data[idx]

    def __setitem__(self, idx: Any, value: Any) -> None:
        if isinstance(idx, slice):
            self._data[idx] = list(value) if not isinstance(value, (int, float, complex)) else [value] * len(self._data[idx])
        else:
            self._data[idx] = value

    def __repr__(self) -> str:
        head = self._data[:6]
        more = "…" if len(self._data) > 6 else ""
        return f"FArray(shape={self.shape}, dtype={self.dtype}, data={head}{more})"

    # arithmetic
    def _bin(self, other: Any, op: Any) -> "FArray":
        if isinstance(other, FArray):
            return FArray([op(a, b) for a, b in zip(self._data, other._data)], dtype=self.dtype)
        return FArray([op(a, other) for a in self._data], dtype=self.dtype)

    def __add__(self, o: Any) -> "FArray":
        return self._bin(o, lambda a, b: a + b)

    def __radd__(self, o: Any) -> "FArray":
        return self._bin(o, lambda a, b: b + a)

    def __sub__(self, o: Any) -> "FArray":
        return self._bin(o, lambda a, b: a - b)

    def __rsub__(self, o: Any) -> "FArray":
        return self._bin(o, lambda a, b: b - a)

    def __mul__(self, o: Any) -> "FArray":
        return self._bin(o, lambda a, b: a * b)

    def __rmul__(self, o: Any) -> "FArray":
        return self._bin(o, lambda a, b: b * a)

    def __truediv__(self, o: Any) -> "FArray":
        return self._bin(o, lambda a, b: a / b)

    def __pow__(self, o: Any) -> "FArray":
        return self._bin(o, lambda a, b: a ** b)

    def __neg__(self) -> "FArray":
        return FArray([-a for a in self._data], dtype=self.dtype)

    def __iadd__(self, o: Any) -> "FArray":
        other = o._data if isinstance(o, FArray) else [o] * len(self._data)
        if not isinstance(o, FArray):
            self._data = [a + o for a in self._data]
        else:
            self._data = [a + b for a, b in zip(self._data, other)]
        return self

    def __imul__(self, o: Any) -> "FArray":
        if isinstance(o, FArray):
            self._data = [a * b for a, b in zip(self._data, o._data)]
        else:
            self._data = [a * o for a in self._data]
        return self

    @property
    def real(self) -> "FArray":
        return FArray([complex(x).real for x in self._data], dtype="float64")

    @property
    def imag(self) -> "FArray":
        return FArray([complex(x).imag for x in self._data], dtype="float64")

    def astype(self, dtype: Any) -> "FArray":
        name = dtype if isinstance(dtype, str) else getattr(dtype, "__name__", str(dtype))
        if "complex" in name:
            return FArray([complex(x) for x in self._data], dtype="complex64")
        if "int" in name or name == "uint8":
            return FArray([int(complex(x).real) for x in self._data], dtype="int32")
        return FArray([float(complex(x).real) if not isinstance(x, complex) else float(x.real) for x in self._data], dtype="float64")

    def copy(self) -> "FArray":
        return FArray(list(self._data), dtype=self.dtype)

    def tolist(self) -> list[Any]:
        return list(self._data)

    def mean(self) -> float:
        if not self._data:
            return 0.0
        return sum(float(complex(x).real) for x in self._data) / len(self._data)

    def max(self) -> float:
        return max(float(complex(x).real) for x in self._data) if self._data else 0.0

    def min(self) -> float:
        return min(float(complex(x).real) for x in self._data) if self._data else 0.0

    def sum(self) -> Any:
        return sum(self._data) if self._data else 0


def array(data: Any, dtype: str = "float64") -> FArray:
    if isinstance(data, FArray):
        return data.astype(dtype) if dtype else data.copy()
    if isinstance(data, (list, tuple)):
        return FArray(data, dtype=dtype)
    try:
        return FArray(list(data), dtype=dtype)
    except TypeError:
        return FArray([data], dtype=dtype)


def zeros(n: int, dtype: str = "float64") -> FArray:
    if "complex" in dtype:
        return FArray([0j] * int(n), dtype=dtype)
    return FArray([0.0] * int(n), dtype=dtype)


def ones(n: int, dtype: str = "float64") -> FArray:
    if "complex" in dtype:
        return FArray([1 + 0j] * int(n), dtype=dtype)
    return FArray([1.0] * int(n), dtype=dtype)


def linspace(a: float, b: float, n: int) -> FArray:
    if n <= 1:
        return FArray([float(a)], dtype="float64")
    step = (b - a) / (n - 1)
    return FArray([a + i * step for i in range(n)], dtype="float64")


def arange(n: int, dtype: str = "float64") -> FArray:
    return FArray(list(range(int(n))), dtype=dtype)


def abs(a: FArray | Sequence[Any]) -> FArray:  # noqa: A001
    data = a._data if isinstance(a, FArray) else list(a)
    return FArray([math.hypot(complex(x).real, complex(x).imag) if isinstance(x, complex) else abs(float(x)) for x in data], dtype="float64")


def log(a: FArray | Sequence[Any]) -> FArray:
    data = a._data if isinstance(a, FArray) else list(a)
    return FArray([math.log(max(float(complex(x).real), 1e-300)) for x in data], dtype="float64")


def log10(a: FArray | Sequence[Any]) -> FArray:
    data = a._data if isinstance(a, FArray) else list(a)
    return FArray([math.log10(max(float(complex(x).real), 1e-300)) for x in data], dtype="float64")


def exp(a: FArray | Sequence[Any]) -> FArray:
    data = a._data if isinstance(a, FArray) else list(a)
    return FArray([math.exp(float(complex(x).real)) for x in data], dtype="float64")


def sqrt(a: FArray | Sequence[Any]) -> FArray:
    data = a._data if isinstance(a, FArray) else list(a)
    return FArray([math.sqrt(max(float(complex(x).real), 0.0)) for x in data], dtype="float64")


def mean(a: FArray | Sequence[Any]) -> float:
    if isinstance(a, FArray):
        return a.mean()
    xs = list(a)
    return sum(float(complex(x).real) for x in xs) / max(len(xs), 1)


def amax(a: FArray | Sequence[Any]) -> float:
    if isinstance(a, FArray):
        return a.max()
    return max(float(complex(x).real) for x in a)


def amin(a: FArray | Sequence[Any]) -> float:
    if isinstance(a, FArray):
        return a.min()
    return min(float(complex(x).real) for x in a)


def median(a: FArray | Sequence[Any]) -> float:
    xs = sorted(float(complex(x).real) for x in (a._data if isinstance(a, FArray) else a))
    if not xs:
        return 0.0
    mid = len(xs) // 2
    if len(xs) % 2:
        return xs[mid]
    return 0.5 * (xs[mid - 1] + xs[mid])


def clip(a: FArray | Sequence[Any], lo: float, hi: float) -> FArray:
    data = a._data if isinstance(a, FArray) else list(a)
    return FArray([min(hi, max(lo, float(complex(x).real))) for x in data], dtype="float64")


def convolve(a: Sequence[float] | FArray, v: Sequence[float] | FArray, mode: str = "same") -> FArray:
    aa = list(a._data if isinstance(a, FArray) else a)
    vv = list(v._data if isinstance(v, FArray) else v)
    n, m = len(aa), len(vv)
    if n == 0 or m == 0:
        return FArray([], dtype="float64")
    out_full = [0.0] * (n + m - 1)
    for i, ai in enumerate(aa):
        for j, vj in enumerate(vv):
            out_full[i + j] += float(complex(ai).real) * float(complex(vj).real)
    if mode == "full":
        return FArray(out_full, dtype="float64")
    if mode == "valid":
        return FArray(out_full[m - 1 : n], dtype="float64")
    # same
    start = (m - 1) // 2
    return FArray(out_full[start : start + n], dtype="float64")


def fft(a: Sequence[complex] | FArray) -> FArray:
    vals = [complex(x) for x in (a._data if isinstance(a, FArray) else a)]
    n = len(vals)
    if n == 0:
        return FArray([], dtype="complex64")
    if n & (n - 1) == 0 and n >= 2:
        def _fft(x: list[complex]) -> list[complex]:
            m = len(x)
            if m == 1:
                return x
            even = _fft(x[0::2])
            odd = _fft(x[1::2])
            t = [cmath.exp(-2j * math.pi * k / m) * odd[k] for k in range(m // 2)]
            return [even[k] + t[k] for k in range(m // 2)] + [even[k] - t[k] for k in range(m // 2)]
        return FArray(_fft(vals), dtype="complex64")
    out = []
    for k in range(n):
        s = sum(vals[j] * cmath.exp(-2j * math.pi * k * j / n) for j in range(n))
        out.append(s)
    return FArray(out, dtype="complex64")


class _RandomGen:
    def __init__(self, seed: int | None = None):
        self._rng = random.Random(seed)

    def standard_normal(self, n: int) -> FArray:
        # Box-Muller
        out = []
        while len(out) < n:
            u1 = max(self._rng.random(), 1e-12)
            u2 = self._rng.random()
            z0 = math.sqrt(-2.0 * math.log(u1)) * math.cos(2 * math.pi * u2)
            z1 = math.sqrt(-2.0 * math.log(u1)) * math.sin(2 * math.pi * u2)
            out.append(z0)
            if len(out) < n:
                out.append(z1)
        return FArray(out[:n], dtype="float64")


def default_rng(seed: int | None = None) -> _RandomGen:
    return _RandomGen(seed)


class _RandomNS:
    @staticmethod
    def default_rng(seed: int | None = None) -> _RandomGen:
        return default_rng(seed)


random_ns = _RandomNS()  # numpy.random-like


def mgrid_2d(h: int, w: int) -> tuple[list[list[float]], list[list[float]]]:
    ys = [[float(y) for _ in range(w)] for y in range(h)]
    xs = [[float(x) for x in range(w)] for _ in range(h)]
    return ys, xs


def asarray(data: Any, dtype: str = "float64") -> FArray:
    return array(data, dtype=dtype)


def float64(x: Any = 0.0) -> float:
    return float(x)


def complex64(x: Any = 0j) -> complex:
    return complex(x)


def uint8(x: Any = 0) -> int:
    return int(x) & 0xFF


# numpy-compatible module surface
class _FFTNS:
    @staticmethod
    def fft(a: Any) -> FArray:
        return fft(a)


fft_ns = _FFTNS()


def numpy_shim() -> Any:
    """Return a module-like object mimicking a tiny numpy subset."""
    import types
    mod = types.SimpleNamespace(
        array=array,
        zeros=zeros,
        ones=ones,
        linspace=linspace,
        arange=arange,
        abs=abs,
        log=log,
        log10=log10,
        exp=exp,
        sqrt=sqrt,
        mean=mean,
        max=amax,
        min=amin,
        median=median,
        clip=clip,
        convolve=convolve,
        asarray=asarray,
        float64=float,
        float32=float,
        complex64=complex,
        complex128=complex,
        int32=int,
        uint8=int,
        fft=fft_ns,
        random=random_ns,
        ndarray=FArray,
        FArray=FArray,
        field_native=True,
        ironclad_cite=IRONCLAD,
    )
    return mod


def ready() -> bool:
    return True
