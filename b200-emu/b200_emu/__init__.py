"""b200-emu: an architecturally-faithful software emulator of a Blackwell B200-class GPU.

This package models the public Blackwell architecture (SMs, warps, 5th-gen tensor
cores, HBM3e memory hierarchy, CUDA-style kernel launches) in Python. It is NOT
the same as a physical B200 — it is a simulation. Heavy compute is dispatched to
host BLAS via numpy for usable speed.
"""

from b200_emu.device import B200Device, get_device
from b200_emu.kernel import KernelContext, kernel, launch
from b200_emu.memory import DeviceArray, to_device, to_host
from b200_emu.tensor_core import DType, tensor_core_mma

__all__ = [
    "B200Device",
    "DType",
    "DeviceArray",
    "KernelContext",
    "get_device",
    "kernel",
    "launch",
    "tensor_core_mma",
    "to_device",
    "to_host",
]

__version__ = "0.1.0"
