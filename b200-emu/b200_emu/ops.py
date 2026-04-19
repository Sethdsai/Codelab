"""High-level device ops that run on the emulator.

These are the primitives a training loop calls (GEMM, elementwise add, ReLU,
softmax cross-entropy, layer-norm, ...). Each op:

  1. Validates inputs are DeviceArrays resident in HBM.
  2. Accounts for the memory traffic + SM execution it would incur on B200.
  3. Performs the computation via numpy (BLAS-backed for GEMM) for speed.

This is how we hit "architecturally like B200" + "actually fast enough to
train something": the *model* of execution is B200, but the arithmetic is
done by OpenBLAS/MKL.
"""

from __future__ import annotations

import numpy as np

from b200_emu.device import B200Device, get_device
from b200_emu.memory import DeviceArray
from b200_emu.tensor_core import DType, tensor_core_mma


def _check(a: DeviceArray) -> None:
    if not isinstance(a, DeviceArray):
        raise TypeError(f"expected DeviceArray, got {type(a).__name__}")


def _wrap(data: np.ndarray, dev: B200Device) -> DeviceArray:
    return dev.hbm.memcpy_h2d(data)


def gemm(
    a: DeviceArray,
    b: DeviceArray,
    c: DeviceArray | None = None,
    *,
    in_dtype: DType = DType.BF16,
    acc_dtype: DType = DType.FP32,
    device: B200Device | None = None,
) -> DeviceArray:
    """D = A @ B + C via 5th-gen tensor cores."""
    _check(a)
    _check(b)
    if c is not None:
        _check(c)
    dev = device if device is not None else get_device()

    d = tensor_core_mma(
        a.data,
        b.data,
        c.data if c is not None else None,
        in_dtype=in_dtype,
        acc_dtype=acc_dtype,
        stats=dev.tc_stats,
    )
    # Charge the HBM traffic.
    dev.mem_stats.hbm_bytes_read += a.nbytes + b.nbytes + (c.nbytes if c is not None else 0)
    dev.mem_stats.hbm_bytes_written += int(d.nbytes)
    return _wrap(d.astype(np.float32, copy=False), dev)


def add(a: DeviceArray, b: DeviceArray, device: B200Device | None = None) -> DeviceArray:
    _check(a)
    _check(b)
    dev = device if device is not None else get_device()
    out = a.data + b.data
    dev.mem_stats.hbm_bytes_read += a.nbytes + b.nbytes
    dev.mem_stats.hbm_bytes_written += int(out.nbytes)
    return _wrap(out, dev)


def mul(a: DeviceArray, b: DeviceArray, device: B200Device | None = None) -> DeviceArray:
    _check(a)
    _check(b)
    dev = device if device is not None else get_device()
    out = a.data * b.data
    dev.mem_stats.hbm_bytes_read += a.nbytes + b.nbytes
    dev.mem_stats.hbm_bytes_written += int(out.nbytes)
    return _wrap(out, dev)


def relu(a: DeviceArray, device: B200Device | None = None) -> DeviceArray:
    _check(a)
    dev = device if device is not None else get_device()
    out = np.maximum(a.data, 0)
    dev.mem_stats.hbm_bytes_read += a.nbytes
    dev.mem_stats.hbm_bytes_written += int(out.nbytes)
    return _wrap(out, dev)


def softmax_cross_entropy(
    logits: DeviceArray,
    labels: np.ndarray,
    device: B200Device | None = None,
) -> tuple[float, DeviceArray]:
    """Return (mean loss, dlogits)."""
    _check(logits)
    dev = device if device is not None else get_device()
    x = logits.data.astype(np.float32)
    x = x - x.max(axis=-1, keepdims=True)
    expx = np.exp(x)
    probs = expx / expx.sum(axis=-1, keepdims=True)
    n = x.shape[0]
    one_hot = np.zeros_like(probs)
    one_hot[np.arange(n), labels] = 1.0
    loss = float(-(one_hot * np.log(probs + 1e-20)).sum() / n)
    grad = (probs - one_hot) / n
    dev.mem_stats.hbm_bytes_read += logits.nbytes
    dev.mem_stats.hbm_bytes_written += int(grad.nbytes)
    return loss, _wrap(grad, dev)
