"""Vector add kernel on the emulated B200.

Run:  python -m examples.vector_add
"""

from __future__ import annotations

import numpy as np

from b200_emu.device import get_device
from b200_emu.kernel import launch
from b200_emu.memory import to_device, to_host


def main() -> None:
    dev = get_device()
    print(dev.spec.describe())
    print()

    n = 1 << 20
    block_size = 256
    grid = (n + block_size - 1) // block_size

    a = to_device(np.random.randn(n).astype(np.float32))
    b = to_device(np.random.randn(n).astype(np.float32))
    c = to_device(np.zeros(n, dtype=np.float32))

    @launch(grid=grid, block=block_size)
    def vadd(ctx, a, b, c):
        tid = ctx.global_thread_ids(axis=0)
        mask = tid < n
        idx = tid[mask]
        c.data[idx] = a.data[idx] + b.data[idx]

    vadd(a, b, c)
    out = to_host(c)
    ref = to_host(a) + to_host(b)
    err = float(np.max(np.abs(out - ref)))
    print(f"vector add (n={n}): max |err| = {err:g}")
    print(f"kernels launched: {dev.stats.kernels_launched}")
    print(f"blocks:           {dev.stats.total_blocks}")
    print(f"threads:          {dev.stats.total_threads}")


if __name__ == "__main__":
    main()
