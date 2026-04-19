"""CUDA-style kernel launch API.

Users write plain Python functions that take a :class:`KernelContext` (which
exposes grid/block/thread indices and the device) plus their arguments, and
launch them with :func:`launch(grid, block)(fn)(*args)` — the same mental
model as ``kernel<<<grid, block>>>(args...)`` in CUDA C++.

Internally the launcher iterates over blocks and records execution on the
emulated SMs. The per-thread work is expressed in the kernel body itself;
the body is called once per block and is responsible for describing the
work all threads do, which is the same pattern used by Triton / Numba.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import numpy as np

from b200_emu.device import B200Device, get_device


@dataclass
class KernelContext:
    device: B200Device
    grid: tuple[int, int, int]
    block: tuple[int, int, int]
    block_idx: tuple[int, int, int]

    @property
    def block_dim(self) -> tuple[int, int, int]:
        return self.block

    @property
    def grid_dim(self) -> tuple[int, int, int]:
        return self.grid

    def thread_range(self) -> np.ndarray:
        """Flat thread ids 0..block_size-1 as a numpy array (SIMT vector)."""
        bs = self.block[0] * self.block[1] * self.block[2]
        return np.arange(bs, dtype=np.int64)

    def global_thread_ids(self, axis: int = 0) -> np.ndarray:
        """Global thread id along ``axis`` (0,1,2) for this block."""
        bx, by, bz = self.block
        ix, iy, iz = self.block_idx
        bs = bx * by * bz
        tid = np.arange(bs, dtype=np.int64)
        tx = tid % bx
        ty = (tid // bx) % by
        tz = tid // (bx * by)
        if axis == 0:
            return ix * bx + tx
        if axis == 1:
            return iy * by + ty
        if axis == 2:
            return iz * bz + tz
        raise ValueError(axis)


def _as_dim3(x: int | tuple[int, ...]) -> tuple[int, int, int]:
    if isinstance(x, int):
        return (x, 1, 1)
    if len(x) == 1:
        return (x[0], 1, 1)
    if len(x) == 2:
        return (x[0], x[1], 1)
    if len(x) == 3:
        return tuple(x)  # type: ignore[return-value]
    raise ValueError(f"invalid dim3: {x}")


KernelFn = Callable[..., None]


def kernel(fn: KernelFn) -> KernelFn:
    """Decorator; currently a no-op tag used for readability."""
    fn.__b200_kernel__ = True  # type: ignore[attr-defined]
    return fn


def launch(
    grid: int | tuple[int, ...],
    block: int | tuple[int, ...],
    *,
    device: B200Device | None = None,
    insts_per_thread: int = 8,
) -> Callable[[KernelFn], Callable[..., None]]:
    """Kernel-launch decorator. Use as ``launch(grid, block)(fn)(*args)``."""

    g = _as_dim3(grid)
    b = _as_dim3(block)
    dev = device if device is not None else get_device()

    def bind(fn: KernelFn) -> Callable[..., None]:
        def run(*args: Any, **kwargs: Any) -> None:
            bs = b[0] * b[1] * b[2]
            total_blocks = g[0] * g[1] * g[2]
            dev.stats.kernels_launched += 1
            dev.stats.total_blocks += total_blocks
            dev.stats.total_threads += total_blocks * bs
            for iz in range(g[2]):
                for iy in range(g[1]):
                    for ix in range(g[0]):
                        ctx = KernelContext(
                            device=dev,
                            grid=g,
                            block=b,
                            block_idx=(ix, iy, iz),
                        )
                        fn(ctx, *args, **kwargs)
                        linear_block = iz * g[0] * g[1] + iy * g[0] + ix
                        sm = dev.sms[linear_block % dev.spec.num_sms]
                        sm.execute_block(num_threads=bs, insts_per_thread=insts_per_thread)

        run.__wrapped__ = fn  # type: ignore[attr-defined]
        return run

    return bind
