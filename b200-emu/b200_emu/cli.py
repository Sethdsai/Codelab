"""Command-line ``b200-smi`` — nvidia-smi-style info tool for the emulator."""

from __future__ import annotations

import argparse
import json

from b200_emu.backend import get_backend
from b200_emu.device import get_device
from b200_emu.specs import B200


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="b200-smi",
        description="Query the b200-emu emulated B200 device.",
    )
    parser.add_argument(
        "--format", choices=["text", "json"], default="text", help="Output format."
    )
    args = parser.parse_args(argv)

    dev = get_device()
    backend = get_backend()
    if args.format == "json":
        payload = {
            "name": B200.name,
            "architecture": B200.architecture,
            "compute_capability": list(B200.compute_capability),
            "num_sms": B200.num_sms,
            "num_tensor_cores": B200.num_tensor_cores,
            "hbm_capacity_bytes": B200.hbm_capacity_bytes,
            "hbm_bandwidth_gbps": B200.hbm_bandwidth_gbps,
            "peak_fp8_tflops": B200.peak_fp8_tflops,
            "peak_bf16_tflops": B200.peak_bf16_tflops,
            "emulated": True,
            "backend": backend.name,
            "backend_device": backend.device_desc,
            "hbm_used_bytes": dev.hbm.used,
            "kernels_launched": dev.stats.kernels_launched,
        }
        print(json.dumps(payload, indent=2))
    else:
        print(dev.summary())
        print(f"\nCompute backend:   {backend.name}  ({backend.device_desc})")
        print("[note] This is b200-emu, a software emulator — not a physical B200.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
