"""Train a tiny MLP on synthetic data using the emulated B200.

Every matmul goes through the 5th-gen tensor-core model (BF16 inputs, FP32
accumulate), so the run actually exercises the B200 datapath we model.

Run:  python -m examples.train_mlp
"""

from __future__ import annotations

import numpy as np

from b200_emu.device import get_device
from b200_emu.memory import to_device
from b200_emu.nn import MLP


def make_dataset(n: int = 1024, d: int = 32, k: int = 8, seed: int = 0):
    rng = np.random.default_rng(seed)
    # Planted linear classifier with nonlinear decision boundary.
    W = rng.standard_normal((d, k)).astype(np.float32)
    x = rng.standard_normal((n, d)).astype(np.float32)
    logits = np.tanh(x) @ W
    y = logits.argmax(axis=1)
    return x, y


def main() -> None:
    dev = get_device()
    print(f"Training on: {dev.spec.name} (emulated)")
    x_host, y_host = make_dataset()
    x = to_device(x_host)

    np.random.seed(0)
    model = MLP(in_features=32, hidden=128, out_features=8)

    for step in range(301):
        loss = model.step(x, y_host, lr=5e-2)
        if step % 50 == 0:
            # Evaluate accuracy.
            logits = model.forward(x)
            acc = float((logits.data.argmax(axis=1) == y_host).mean())
            print(f"step {step:4d}  loss={loss:.4f}  acc={acc*100:.1f}%")

    print()
    print(f"Tensor-core MMAs: {dev.tc_stats.mma_ops}")
    print(f"Tensor-core work: {dev.tc_stats.flops / 1e9:.2f} GFLOP")
    print(f"HBM bytes R/W:    {dev.mem_stats.hbm_bytes_read} / {dev.mem_stats.hbm_bytes_written}")


if __name__ == "__main__":
    main()
