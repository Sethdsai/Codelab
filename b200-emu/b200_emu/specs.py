"""Public Blackwell B200 specifications.

These numbers are drawn from NVIDIA's public Blackwell / B200 disclosures and
GTC announcements. They describe the *logical* architecture the emulator
models. They are NOT NVIDIA proprietary microarchitectural details.

References (public):
  * NVIDIA Blackwell architecture whitepaper
  * GTC 2024 Blackwell keynote
  * HGX B200 datasheet
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class B200Spec:
    name: str = "NVIDIA B200"
    architecture: str = "Blackwell"
    compute_capability: tuple[int, int] = (10, 0)

    # Two reticle-sized dies, fused via 10 TB/s NV-HBI, exposed as one logical GPU.
    num_dies: int = 2
    sms_per_die: int = 104
    num_sms: int = 208  # 2 * 104

    # Per-SM resources (Blackwell SM, public figures).
    warp_schedulers_per_sm: int = 4
    threads_per_warp: int = 32
    max_warps_per_sm: int = 64
    max_threads_per_sm: int = 2048
    max_threads_per_block: int = 1024

    # FP32 / INT32 / FP64 lanes per SM (public Blackwell SM layout).
    fp32_cores_per_sm: int = 128
    int32_cores_per_sm: int = 64
    fp64_cores_per_sm: int = 64

    # 5th-gen tensor cores (4 per SM, one per warp scheduler).
    tensor_cores_per_sm: int = 4
    num_tensor_cores: int = 208 * 4  # 832

    # On-chip memory (per SM).
    register_file_bytes_per_sm: int = 256 * 1024  # 256 KB
    l1_smem_bytes_per_sm: int = 228 * 1024  # unified L1 / shared, 228 KB

    # Global / L2 memory.
    l2_cache_bytes: int = 60 * 1024 * 1024  # 60 MB shared L2 (public figure)
    hbm_capacity_bytes: int = 192 * 1024**3  # 192 GB HBM3e
    hbm_bandwidth_gbps: int = 8_000  # ~8 TB/s aggregate

    # Clocks (nominal boost).
    sm_clock_mhz: int = 2_100

    # Peak throughputs (public, dense, no sparsity).
    peak_fp4_tflops: float = 20_000.0  # 20 PFLOPS FP4
    peak_fp8_tflops: float = 10_000.0  # 10 PFLOPS FP8
    peak_fp16_tflops: float = 5_000.0
    peak_bf16_tflops: float = 5_000.0
    peak_tf32_tflops: float = 2_500.0
    peak_fp32_tflops: float = 80.0  # non-tensor-core FP32
    peak_fp64_tflops: float = 40.0

    # Interconnect.
    nvlink_version: int = 5
    nvlink_bandwidth_gbps: int = 1_800  # 1.8 TB/s
    pcie_gen: int = 5

    # TDP
    tdp_watts: int = 1_000

    def describe(self) -> str:
        """Multi-line human-readable description, nvidia-smi-style."""
        gb = 1024**3
        lines = [
            f"{self.name}  (Architecture: {self.architecture}, "
            f"Compute {self.compute_capability[0]}.{self.compute_capability[1]})",
            f"  Dies:              {self.num_dies}  "
            f"({self.sms_per_die} SMs/die, {self.num_sms} total)",
            f"  Tensor cores:      {self.num_tensor_cores} "
            f"({self.tensor_cores_per_sm}/SM, 5th-gen)",
            f"  HBM3e:             {self.hbm_capacity_bytes // gb} GB  "
            f"@ {self.hbm_bandwidth_gbps} GB/s",
            f"  L2 cache:          {self.l2_cache_bytes // (1024*1024)} MB",
            f"  SM clock (boost):  {self.sm_clock_mhz} MHz",
            f"  NVLink {self.nvlink_version}:         {self.nvlink_bandwidth_gbps} GB/s",
            f"  TDP:               {self.tdp_watts} W",
            "  Peak throughput (dense):",
            f"    FP4 tensor:   {self.peak_fp4_tflops:>7.0f} TFLOPS",
            f"    FP8 tensor:   {self.peak_fp8_tflops:>7.0f} TFLOPS",
            f"    BF16 tensor:  {self.peak_bf16_tflops:>7.0f} TFLOPS",
            f"    FP16 tensor:  {self.peak_fp16_tflops:>7.0f} TFLOPS",
            f"    TF32 tensor:  {self.peak_tf32_tflops:>7.0f} TFLOPS",
            f"    FP32 cuda:    {self.peak_fp32_tflops:>7.0f} TFLOPS",
            f"    FP64 cuda:    {self.peak_fp64_tflops:>7.0f} TFLOPS",
        ]
        return "\n".join(lines)


B200 = B200Spec()
