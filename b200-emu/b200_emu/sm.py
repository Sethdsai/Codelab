"""Streaming Multiprocessor and warp scheduler model.

Each B200 SM has:
  * 4 warp schedulers (each with its own 5th-gen tensor core)
  * 128 FP32 + 64 INT32 + 64 FP64 ALU lanes
  * 256 KB register file
  * 228 KB unified L1 / shared memory
  * Up to 64 resident warps (2048 threads)

The emulator models warps as logical groups of 32 threads. At execution time,
a warp's work is expressed as vectorized numpy operations over the thread-lane
dimension — mirroring the SIMT execution model while staying fast.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from b200_emu.memory import SharedMemory
from b200_emu.specs import B200, B200Spec
from b200_emu.tensor_core import TensorCoreStats


@dataclass
class WarpSchedulerStats:
    warps_issued: int = 0
    instructions_issued: int = 0
    tensor_core_issues: int = 0
    stalls: int = 0


@dataclass
class WarpScheduler:
    sm_id: int
    sched_id: int
    tensor_core_stats: TensorCoreStats = field(default_factory=TensorCoreStats)
    stats: WarpSchedulerStats = field(default_factory=WarpSchedulerStats)

    def issue(self, warps: int, insts_per_warp: int) -> None:
        self.stats.warps_issued += warps
        self.stats.instructions_issued += warps * insts_per_warp

    def issue_tensor_core(self) -> None:
        self.stats.tensor_core_issues += 1


@dataclass
class SMStats:
    blocks_executed: int = 0
    warps_executed: int = 0
    instructions_executed: int = 0
    cycles: int = 0


@dataclass
class StreamingMultiprocessor:
    sm_id: int
    spec: B200Spec = B200
    shared: SharedMemory = field(init=False)
    schedulers: list[WarpScheduler] = field(init=False)
    stats: SMStats = field(default_factory=SMStats)

    def __post_init__(self) -> None:
        self.shared = SharedMemory(sm_id=self.sm_id, capacity=self.spec.l1_smem_bytes_per_sm)
        self.schedulers = [
            WarpScheduler(sm_id=self.sm_id, sched_id=i)
            for i in range(self.spec.warp_schedulers_per_sm)
        ]

    def execute_block(self, num_threads: int, insts_per_thread: int) -> None:
        """Account for executing one CTA of ``num_threads`` threads."""
        if num_threads > self.spec.max_threads_per_block:
            raise ValueError(
                f"block size {num_threads} exceeds B200 max "
                f"{self.spec.max_threads_per_block}"
            )
        warps = (num_threads + self.spec.threads_per_warp - 1) // self.spec.threads_per_warp
        # Round-robin warps across the 4 schedulers.
        for w in range(warps):
            self.schedulers[w % self.spec.warp_schedulers_per_sm].issue(1, insts_per_thread)
        self.stats.blocks_executed += 1
        self.stats.warps_executed += warps
        self.stats.instructions_executed += warps * insts_per_thread
        # Rough cycle estimate: 1 IPC per scheduler.
        self.stats.cycles += (
            insts_per_thread * warps + self.spec.warp_schedulers_per_sm - 1
        ) // self.spec.warp_schedulers_per_sm

    def reset(self) -> None:
        self.stats = SMStats()
        for s in self.schedulers:
            s.stats = WarpSchedulerStats()
        self.shared.buffers.clear()
