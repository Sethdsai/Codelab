"""Tensor-core GEMM benchmark across dtypes (BF16 / FP16 / TF32 / FP8).

Run:  python -m examples.gemm_bench
"""

from __future__ import annotations

import time

import numpy as np

from b200_emu.device import get_device
from b200_emu.memory import to_device
from b200_emu.ops import gemm
from b200_emu.tensor_core import DType


def bench(dtype: DType, m: int = 1024, n: int = 1024, k: int = 1024) -> None:
    a = to_device(np.random.randn(m, k).astype(np.float32))
    b = to_device(np.random.randn(k, n).astype(np.float32))

    # warmup
    gemm(a, b, in_dtype=dtype)

    iters = 5
    t0 = time.perf_counter()
    for _ in range(iters):
        gemm(a, b, in_dtype=dtype)
    dt = (time.perf_counter() - t0) / iters
    flops = 2 * m * n * k
    tflops = flops / dt / 1e12
    print(f"  {dtype.value:<12s}  {dt*1e3:7.2f} ms   {tflops:6.2f} TFLOPS (emu host BLAS)")


def main() -> None:
    dev = get_device()
    print("B200 (emulated) GEMM benchmark")
    print(f"  device : {dev.spec.name}")
    print(f"  peak   : FP8 {dev.spec.peak_fp8_tflops} / BF16 {dev.spec.peak_bf16_tflops} TFLOPS")
    print()
    for dtype in (DType.FP32, DType.TF32, DType.BF16, DType.FP16, DType.FP8_E4M3):
        bench(dtype)
    print()
    print("Note: TFLOPS numbers above reflect host-BLAS throughput, not B200 hardware.")


if __name__ == "__main__":
    main()
