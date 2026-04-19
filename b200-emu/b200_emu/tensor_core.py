"""5th-generation Blackwell tensor core model.

Blackwell tensor cores expose warp-group MMA (wgmma) operations over tiles
with types FP4, FP6, FP8 (E4M3 / E5M2), FP16, BF16, TF32, FP64. We model a
usable subset: FP8 (E4M3), FP16, BF16, TF32, and the FP8->FP16 accumulate
pattern used during FP8 training.

For performance we dispatch the actual MMA to numpy's BLAS (GEMM) after
quantizing inputs to the target dtype and dequantizing back. This preserves
the numerical behavior of low-precision training while running at host-BLAS
speed — orders of magnitude faster than Python loops.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

import numpy as np


class DType(str, Enum):
    FP4_E2M1 = "fp4_e2m1"
    FP6_E3M2 = "fp6_e3m2"
    FP8_E4M3 = "fp8_e4m3"
    FP8_E5M2 = "fp8_e5m2"
    FP16 = "fp16"
    BF16 = "bf16"
    TF32 = "tf32"
    FP32 = "fp32"
    FP64 = "fp64"


# Supported tile shapes for Blackwell wgmma (public subset).
SUPPORTED_WGMMA_SHAPES: tuple[tuple[int, int, int], ...] = (
    (64, 8, 16),
    (64, 16, 16),
    (64, 32, 16),
    (64, 64, 16),
    (64, 128, 16),
    (64, 256, 16),
)


@dataclass
class TensorCoreStats:
    mma_ops: int = 0
    flops: int = 0
    bytes_in: int = 0
    bytes_out: int = 0
    per_dtype_flops: dict[str, int] = field(default_factory=dict)

    def record(self, dtype: DType, flops: int, bytes_in: int, bytes_out: int) -> None:
        self.mma_ops += 1
        self.flops += flops
        self.bytes_in += bytes_in
        self.bytes_out += bytes_out
        self.per_dtype_flops[dtype.value] = self.per_dtype_flops.get(dtype.value, 0) + flops


def _quantize_fp8_e4m3(x: np.ndarray) -> np.ndarray:
    """Quantize to FP8 E4M3 (1-bit sign, 4-bit exp, 3-bit mantissa).

    FP8 E4M3 has max ~448.0. We clip and round-to-nearest-even at mantissa
    resolution. This models numerical behavior; the returned array is
    float32-backed for downstream BLAS.
    """
    x = np.asarray(x, dtype=np.float32)
    fp8_max = 448.0
    x = np.clip(x, -fp8_max, fp8_max)
    # Decompose into sign, exponent, mantissa using float bits.
    sign = np.sign(x)
    ax = np.abs(x)
    # Smallest normal in E4M3 is 2^-6 = 1/64; subnormals go down to 2^-9.
    with np.errstate(divide="ignore"):
        e = np.floor(np.log2(np.where(ax > 0, ax, 1.0)))
    e = np.clip(e, -9, 8)
    mant_scale = np.power(2.0, e - 3)  # 3 mantissa bits
    q = np.round(ax / mant_scale) * mant_scale
    q = np.where(ax == 0, 0.0, q)
    return (sign * q).astype(np.float32)


def _quantize_fp8_e5m2(x: np.ndarray) -> np.ndarray:
    """Quantize to FP8 E5M2 (1 sign, 5 exp, 2 mantissa). Max ~57344."""
    x = np.asarray(x, dtype=np.float32)
    fp8_max = 57344.0
    x = np.clip(x, -fp8_max, fp8_max)
    sign = np.sign(x)
    ax = np.abs(x)
    with np.errstate(divide="ignore"):
        e = np.floor(np.log2(np.where(ax > 0, ax, 1.0)))
    e = np.clip(e, -16, 15)
    mant_scale = np.power(2.0, e - 2)
    q = np.round(ax / mant_scale) * mant_scale
    q = np.where(ax == 0, 0.0, q)
    return (sign * q).astype(np.float32)


def _quantize_tf32(x: np.ndarray) -> np.ndarray:
    """TF32 = FP32 range with FP16 precision (10 mantissa bits)."""
    x = np.asarray(x, dtype=np.float32)
    # Zero out the low 13 bits of the 23-bit mantissa.
    bits = x.view(np.uint32).copy()
    bits &= np.uint32(0xFFFFE000)
    return bits.view(np.float32)


def _cast_in(x: np.ndarray, dtype: DType) -> np.ndarray:
    if dtype is DType.FP16:
        return x.astype(np.float16).astype(np.float32)
    if dtype is DType.BF16:
        # bfloat16 = FP32 with low 16 mantissa bits zeroed.
        bits = x.astype(np.float32).view(np.uint32).copy()
        bits &= np.uint32(0xFFFF0000)
        return bits.view(np.float32)
    if dtype is DType.TF32:
        return _quantize_tf32(x)
    if dtype is DType.FP8_E4M3:
        return _quantize_fp8_e4m3(x)
    if dtype is DType.FP8_E5M2:
        return _quantize_fp8_e5m2(x)
    if dtype is DType.FP32:
        return x.astype(np.float32)
    if dtype is DType.FP64:
        return x.astype(np.float64)
    raise NotImplementedError(f"dtype {dtype} not supported for tensor-core input")


def tensor_core_mma(
    a: np.ndarray,
    b: np.ndarray,
    c: np.ndarray | None = None,
    *,
    in_dtype: DType = DType.BF16,
    acc_dtype: DType = DType.FP32,
    stats: TensorCoreStats | None = None,
) -> np.ndarray:
    """Warp-group MMA: D = A @ B + C with input quantization + FP32 accumulate.

    Matches the semantics of Blackwell's wgmma: inputs are quantized to
    ``in_dtype``, multiplied, and accumulated into ``acc_dtype`` (default
    FP32). ``c`` is optional; if provided its shape must match A @ B.

    Under the hood this calls numpy.matmul, which uses OpenBLAS / MKL —
    vastly faster than a Python loop while preserving the numerical effect
    of low-precision inputs.
    """
    if a.ndim != 2 or b.ndim != 2:
        raise ValueError("tensor_core_mma expects 2D A and B")
    M, K = a.shape
    K2, N = b.shape
    if K != K2:
        raise ValueError(f"shape mismatch: A is {a.shape}, B is {b.shape}")

    acc_np = np.float64 if acc_dtype is DType.FP64 else np.float32

    a_q = _cast_in(a, in_dtype).astype(acc_np, copy=False)
    b_q = _cast_in(b, in_dtype).astype(acc_np, copy=False)
    d = a_q @ b_q
    if c is not None:
        if c.shape != d.shape:
            raise ValueError(f"C shape {c.shape} != A@B shape {d.shape}")
        d = d + c.astype(acc_np, copy=False)

    if stats is not None:
        flops = 2 * M * N * K
        bytes_in = a.nbytes + b.nbytes + (c.nbytes if c is not None else 0)
        stats.record(in_dtype, flops, bytes_in, int(d.nbytes))
    return d
