import numpy as np
import pytest

from b200_emu.device import B200Device, set_device
from b200_emu.memory import to_device
from b200_emu.nn import MLP


@pytest.fixture(autouse=True)
def fresh_device():
    dev = B200Device()
    set_device(dev)
    yield dev
    set_device(None)


def test_mlp_overfits_tiny_dataset(fresh_device):
    """Sanity: the emulated device can actually train a model."""
    rng = np.random.default_rng(0)
    n, d_in, d_hidden, n_classes = 64, 16, 32, 4
    x_host = rng.standard_normal((n, d_in)).astype(np.float32)
    y_host = rng.integers(0, n_classes, size=n)
    x = to_device(x_host)

    np.random.seed(0)
    model = MLP(d_in, d_hidden, n_classes)

    losses = []
    for _ in range(200):
        loss = model.step(x, y_host, lr=5e-2)
        losses.append(loss)

    assert losses[-1] < losses[0] * 0.5, f"loss did not decrease: {losses[0]} -> {losses[-1]}"
    assert fresh_device.tc_stats.mma_ops > 0
    assert fresh_device.stats.total_threads == 0  # MLP uses ops, not raw kernels
