"""Minimal neural-network building blocks that run on the emulator.

These mirror a tiny subset of torch.nn semantics so we can demonstrate end-to-end
training on the emulated B200. They are intentionally small: Linear, ReLU,
cross-entropy, SGD. Everything runs through :mod:`b200_emu.ops`, i.e. every
matmul goes through the 5th-gen tensor-core model.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from b200_emu.device import get_device
from b200_emu.memory import DeviceArray
from b200_emu.ops import gemm, relu, softmax_cross_entropy
from b200_emu.tensor_core import DType


@dataclass
class Linear:
    in_features: int
    out_features: int
    weight: DeviceArray = field(init=False)
    bias: DeviceArray = field(init=False)
    _x_cache: DeviceArray | None = field(init=False, default=None, repr=False)

    def __post_init__(self) -> None:
        dev = get_device()
        scale = np.sqrt(2.0 / self.in_features).astype(np.float32)
        w = (np.random.randn(self.in_features, self.out_features).astype(np.float32) * scale)
        b = np.zeros(self.out_features, dtype=np.float32)
        self.weight = dev.hbm.memcpy_h2d(w)
        self.bias = dev.hbm.memcpy_h2d(b)

    def forward(self, x: DeviceArray, *, in_dtype: DType = DType.BF16) -> DeviceArray:
        self._x_cache = x
        dev = get_device()
        y = gemm(x, self.weight, in_dtype=in_dtype)
        # Add bias (broadcast). Read-modify-write on y, all on device.
        y.data[...] = y.data + self.bias.data
        dev.mem_stats.hbm_bytes_read += self.bias.nbytes
        dev.mem_stats.hbm_bytes_written += int(y.nbytes)
        return y

    def backward(self, dy: DeviceArray, lr: float, *, in_dtype: DType = DType.BF16) -> DeviceArray:
        assert self._x_cache is not None, "must call forward() before backward()"
        x = self._x_cache
        # dW = x^T @ dy ; dx = dy @ W^T ; db = sum(dy, axis=0)
        dev = get_device()
        xT = DeviceArray(data=x.data.T.copy(), dtype_name=x.dtype_name)
        wT = DeviceArray(data=self.weight.data.T.copy(), dtype_name=self.weight.dtype_name)
        dW = gemm(xT, dy, in_dtype=in_dtype)
        dx = gemm(dy, wT, in_dtype=in_dtype)
        db = dy.data.sum(axis=0)
        # SGD update, in place on device memory.
        self.weight.data -= lr * dW.data
        self.bias.data -= lr * db
        dev.mem_stats.hbm_bytes_written += int(self.weight.nbytes + self.bias.nbytes)
        return dx


@dataclass
class ReLU:
    _mask_cache: np.ndarray | None = field(init=False, default=None, repr=False)

    def forward(self, x: DeviceArray) -> DeviceArray:
        self._mask_cache = (x.data > 0).astype(np.float32)
        return relu(x)

    def backward(self, dy: DeviceArray, lr: float) -> DeviceArray:
        assert self._mask_cache is not None
        dev = get_device()
        out = dy.data * self._mask_cache
        return dev.hbm.memcpy_h2d(out)


@dataclass
class MLP:
    """2-layer MLP: Linear -> ReLU -> Linear. Trained with SGD."""

    in_features: int
    hidden: int
    out_features: int

    def __post_init__(self) -> None:
        self.fc1 = Linear(self.in_features, self.hidden)
        self.act = ReLU()
        self.fc2 = Linear(self.hidden, self.out_features)
        self._layers = [self.fc1, self.act, self.fc2]

    def forward(self, x: DeviceArray) -> DeviceArray:
        h = self.fc1.forward(x)
        h = self.act.forward(h)
        return self.fc2.forward(h)

    def step(self, x: DeviceArray, labels: np.ndarray, lr: float) -> float:
        logits = self.forward(x)
        loss, dlogits = softmax_cross_entropy(logits, labels)
        dh = self.fc2.backward(dlogits, lr)
        dh = self.act.backward(dh, lr)
        _ = self.fc1.backward(dh, lr)
        return loss
