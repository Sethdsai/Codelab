"""Top-level B200 device object.

Owns the HBM3e allocator, all 208 SMs, the shared L2 cache model, and
aggregated statistics. A single global device is exposed via ``get_device()``
so that kernel launches and memory transfers can find it without threading
it through every call site — matching the CUDA runtime ergonomics.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from b200_emu.memory import HBM, MemoryStats
from b200_emu.sm import StreamingMultiprocessor
from b200_emu.specs import B200, B200Spec
from b200_emu.tensor_core import TensorCoreStats


@dataclass
class DeviceStats:
    kernels_launched: int = 0
    total_kernel_seconds: float = 0.0
    total_blocks: int = 0
    total_threads: int = 0


class B200Device:
    """Emulated NVIDIA B200 GPU."""

    def __init__(self, spec: B200Spec = B200, device_index: int = 0) -> None:
        self.spec = spec
        self.device_index = device_index
        self.mem_stats = MemoryStats()
        self.tc_stats = TensorCoreStats()
        self.stats = DeviceStats()
        self.hbm = HBM(spec=spec, stats=self.mem_stats)
        self.sms: list[StreamingMultiprocessor] = [
            StreamingMultiprocessor(sm_id=i, spec=spec) for i in range(spec.num_sms)
        ]
        self._boot_time = time.time()

    def reset(self) -> None:
        self.mem_stats.reset()
        self.tc_stats = TensorCoreStats()
        self.stats = DeviceStats()
        self.hbm = HBM(spec=self.spec, stats=self.mem_stats)
        for sm in self.sms:
            sm.reset()

    @property
    def uptime_s(self) -> float:
        return time.time() - self._boot_time

    def summary(self) -> str:
        gb = 1024**3
        used_gb = self.hbm.used / gb
        cap_gb = self.hbm.capacity / gb
        lines = [
            self.spec.describe(),
            "",
            f"Device index:      {self.device_index}",
            f"Uptime:            {self.uptime_s:.1f} s",
            f"HBM used:          {used_gb:.3f} / {cap_gb:.0f} GB",
            f"HBM bytes R/W:     {self.mem_stats.hbm_bytes_read} / "
            f"{self.mem_stats.hbm_bytes_written}",
            f"Kernels launched:  {self.stats.kernels_launched}",
            f"Blocks executed:   {self.stats.total_blocks}",
            f"Threads executed:  {self.stats.total_threads}",
            f"Tensor-core MMAs:  {self.tc_stats.mma_ops} "
            f"({self.tc_stats.flops / 1e9:.2f} GFLOP)",
        ]
        return "\n".join(lines)


_DEVICE: B200Device | None = None


def get_device() -> B200Device:
    global _DEVICE
    if _DEVICE is None:
        _DEVICE = B200Device()
    return _DEVICE


def set_device(device: B200Device | None) -> None:
    """Test/DI helper."""
    global _DEVICE
    _DEVICE = device
