"""Memory hierarchy: HBM3e global memory, L2, per-SM shared memory.

The emulator models the *logical* hierarchy. Physically, all three tiers are
backed by host DRAM (numpy arrays). Access accounting (bytes read / written,
approximate cycles) is tracked so users can reason about B200-like behavior.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from b200_emu.specs import B200, B200Spec


@dataclass
class MemoryStats:
    hbm_bytes_read: int = 0
    hbm_bytes_written: int = 0
    l2_bytes_read: int = 0
    l2_bytes_written: int = 0
    smem_bytes_read: int = 0
    smem_bytes_written: int = 0
    tma_transfers: int = 0
    bytes_allocated: int = 0

    def reset(self) -> None:
        for f in self.__dataclass_fields__:
            setattr(self, f, 0)


@dataclass
class DeviceArray:
    """A tensor resident in emulated HBM3e.

    Wraps a numpy array and records metadata (dtype, shape, device offset).
    Compute ops consume DeviceArray inputs and produce DeviceArray outputs,
    mirroring how CUDA device memory works.
    """

    data: np.ndarray
    dtype_name: str
    device_offset: int = 0

    @property
    def shape(self) -> tuple[int, ...]:
        return tuple(self.data.shape)

    @property
    def nbytes(self) -> int:
        return int(self.data.nbytes)

    def __repr__(self) -> str:
        return (
            f"DeviceArray(shape={self.shape}, dtype={self.dtype_name}, "
            f"offset=0x{self.device_offset:x})"
        )


class HBM:
    """Emulated HBM3e global memory.

    Allocates DeviceArrays and maintains a simple bump allocator over a
    192 GB logical address space. Physical backing is host RAM only for
    allocations that are actually used, so the emulator does not reserve
    hundreds of gigabytes up front.
    """

    def __init__(self, spec: B200Spec = B200, stats: MemoryStats | None = None) -> None:
        self.spec = spec
        self.stats = stats if stats is not None else MemoryStats()
        self._next_offset: int = 0
        self._live: dict[int, DeviceArray] = {}

    @property
    def capacity(self) -> int:
        return self.spec.hbm_capacity_bytes

    @property
    def used(self) -> int:
        return sum(a.nbytes for a in self._live.values())

    def allocate(self, shape: tuple[int, ...], dtype: np.dtype | str) -> DeviceArray:
        dtype = np.dtype(dtype)
        nbytes = int(np.prod(shape)) * dtype.itemsize
        if self.used + nbytes > self.capacity:
            raise MemoryError(
                f"HBM OOM: requested {nbytes} B, already using {self.used} B "
                f"of {self.capacity} B (emulated)."
            )
        offset = self._next_offset
        self._next_offset += nbytes
        arr = DeviceArray(
            data=np.zeros(shape, dtype=dtype),
            dtype_name=dtype.name,
            device_offset=offset,
        )
        self._live[offset] = arr
        self.stats.bytes_allocated += nbytes
        return arr

    def free(self, arr: DeviceArray) -> None:
        self._live.pop(arr.device_offset, None)

    def memcpy_h2d(self, host: np.ndarray) -> DeviceArray:
        """Host-to-device transfer (cudaMemcpy over PCIe)."""
        darr = self.allocate(host.shape, host.dtype)
        darr.data[...] = host
        self.stats.hbm_bytes_written += darr.nbytes
        return darr

    def memcpy_d2h(self, darr: DeviceArray) -> np.ndarray:
        self.stats.hbm_bytes_read += darr.nbytes
        return darr.data.copy()


@dataclass
class SharedMemory:
    """Per-SM unified L1 / shared memory (228 KB on Blackwell SM)."""

    sm_id: int
    capacity: int = B200.l1_smem_bytes_per_sm
    buffers: dict[str, np.ndarray] = field(default_factory=dict)

    def used(self) -> int:
        return sum(b.nbytes for b in self.buffers.values())

    def alloc(self, name: str, shape: tuple[int, ...], dtype: Any) -> np.ndarray:
        dtype = np.dtype(dtype)
        nbytes = int(np.prod(shape)) * dtype.itemsize
        if self.used() + nbytes > self.capacity:
            raise MemoryError(
                f"SM{self.sm_id} shared-mem OOM: requested {nbytes} B, "
                f"{self.used()} B in use of {self.capacity} B"
            )
        buf = np.zeros(shape, dtype=dtype)
        self.buffers[name] = buf
        return buf

    def free(self, name: str) -> None:
        self.buffers.pop(name, None)


def to_device(host: np.ndarray, hbm: HBM | None = None) -> DeviceArray:
    from b200_emu.device import get_device

    hbm = hbm if hbm is not None else get_device().hbm
    return hbm.memcpy_h2d(np.ascontiguousarray(host))


def to_host(darr: DeviceArray, hbm: HBM | None = None) -> np.ndarray:
    from b200_emu.device import get_device

    hbm = hbm if hbm is not None else get_device().hbm
    return hbm.memcpy_d2h(darr)
