"""Compute-backend abstraction.

The B200 *architecture model* (SMs, warps, 5th-gen tensor cores, memory
hierarchy, kernel launches) always runs in Python. But the actual math is
delegated to a backend so we can use whatever real silicon is available:

  * ``numpy``       — default, uses host BLAS (OpenBLAS/MKL). Works everywhere.
  * ``torch-cuda``  — PyTorch on a real NVIDIA GPU. 100–1000× faster than numpy.
  * ``torch-mps``   — PyTorch on Apple Silicon (M1/M2/M3/M4).
  * ``torch-cpu``   — PyTorch on CPU (similar to numpy, sometimes faster).

Selection order (first available wins):
  1. ``B200_EMU_BACKEND`` environment variable, if set.
  2. PyTorch CUDA if ``torch.cuda.is_available()``.
  3. PyTorch MPS if ``torch.backends.mps.is_available()``.
  4. Plain numpy.

All backends expose the same minimal interface used by the emulator's compute
ops. Inputs and outputs are numpy arrays at the emulator boundary, so the rest
of the codebase (memory, DeviceArray, tests) is backend-agnostic.
"""

from __future__ import annotations

import os
from typing import Protocol

import numpy as np


class Backend(Protocol):
    name: str
    device_desc: str

    def matmul(self, a: np.ndarray, b: np.ndarray, acc_dtype: str = "fp32") -> np.ndarray: ...
    def elementwise_add(self, a: np.ndarray, b: np.ndarray) -> np.ndarray: ...
    def elementwise_mul(self, a: np.ndarray, b: np.ndarray) -> np.ndarray: ...
    def relu(self, a: np.ndarray) -> np.ndarray: ...


class NumpyBackend:
    name = "numpy"

    def __init__(self) -> None:
        self.device_desc = "host BLAS (numpy)"

    def matmul(self, a: np.ndarray, b: np.ndarray, acc_dtype: str = "fp32") -> np.ndarray:
        acc = np.float64 if acc_dtype == "fp64" else np.float32
        return np.asarray(a, dtype=acc) @ np.asarray(b, dtype=acc)

    def elementwise_add(self, a: np.ndarray, b: np.ndarray) -> np.ndarray:
        return a + b

    def elementwise_mul(self, a: np.ndarray, b: np.ndarray) -> np.ndarray:
        return a * b

    def relu(self, a: np.ndarray) -> np.ndarray:
        return np.maximum(a, 0)


class TorchBackend:
    """PyTorch-backed compute. Auto-chooses CUDA / MPS / CPU."""

    def __init__(self, device: str) -> None:
        import torch  # lazy

        self._torch = torch
        self._device = torch.device(device)
        self.name = f"torch-{device}"
        if device == "cuda":
            idx = torch.cuda.current_device()
            self.device_desc = f"PyTorch CUDA on {torch.cuda.get_device_name(idx)}"
        elif device == "mps":
            self.device_desc = "PyTorch MPS (Apple Silicon)"
        else:
            self.device_desc = "PyTorch CPU"

    def _to_dev(self, x: np.ndarray, dtype):
        return self._torch.as_tensor(x, dtype=dtype, device=self._device)

    def matmul(self, a: np.ndarray, b: np.ndarray, acc_dtype: str = "fp32") -> np.ndarray:
        torch = self._torch
        dtype = torch.float64 if acc_dtype == "fp64" else torch.float32
        ta = self._to_dev(a, dtype)
        tb = self._to_dev(b, dtype)
        out = ta @ tb
        return out.detach().to("cpu").numpy()

    def elementwise_add(self, a: np.ndarray, b: np.ndarray) -> np.ndarray:
        return a + b  # cheap; keep on host

    def elementwise_mul(self, a: np.ndarray, b: np.ndarray) -> np.ndarray:
        return a * b

    def relu(self, a: np.ndarray) -> np.ndarray:
        return np.maximum(a, 0)


_BACKEND: Backend | None = None


def _try_torch(device: str) -> TorchBackend | None:
    try:
        import torch
    except ImportError:
        return None
    if device == "cuda" and not torch.cuda.is_available():
        return None
    if device == "mps" and not (
        hasattr(torch.backends, "mps") and torch.backends.mps.is_available()
    ):
        return None
    try:
        return TorchBackend(device)
    except Exception:
        return None


def _auto_select() -> Backend:
    for dev in ("cuda", "mps"):
        bk = _try_torch(dev)
        if bk is not None:
            return bk
    return NumpyBackend()


def get_backend() -> Backend:
    global _BACKEND
    if _BACKEND is not None:
        return _BACKEND
    choice = os.environ.get("B200_EMU_BACKEND", "auto").strip().lower()
    if choice in ("", "auto"):
        _BACKEND = _auto_select()
    elif choice == "numpy":
        _BACKEND = NumpyBackend()
    elif choice in ("torch-cuda", "cuda"):
        bk = _try_torch("cuda")
        _BACKEND = bk if bk is not None else NumpyBackend()
    elif choice in ("torch-mps", "mps"):
        bk = _try_torch("mps")
        _BACKEND = bk if bk is not None else NumpyBackend()
    elif choice in ("torch-cpu", "cpu"):
        bk = _try_torch("cpu")
        _BACKEND = bk if bk is not None else NumpyBackend()
    else:
        _BACKEND = NumpyBackend()
    return _BACKEND


def set_backend(backend: Backend | None) -> None:
    """Test/DI helper."""
    global _BACKEND
    _BACKEND = backend
