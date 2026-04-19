import numpy as np
import pytest

from b200_emu.device import B200Device, set_device
from b200_emu.kernel import launch
from b200_emu.memory import to_device, to_host


@pytest.fixture(autouse=True)
def fresh_device():
    dev = B200Device()
    set_device(dev)
    yield dev
    set_device(None)


def test_vector_add_kernel(fresh_device):
    n = 4096
    block_size = 256
    grid = (n + block_size - 1) // block_size

    a = to_device(np.arange(n, dtype=np.float32))
    b = to_device(np.arange(n, dtype=np.float32) * 2)
    c = to_device(np.zeros(n, dtype=np.float32))

    @launch(grid=grid, block=block_size)
    def vadd(ctx, a, b, c):
        tid = ctx.global_thread_ids(axis=0)
        mask = tid < n
        idx = tid[mask]
        c.data[idx] = a.data[idx] + b.data[idx]

    vadd(a, b, c)

    np.testing.assert_array_equal(to_host(c), np.arange(n) * 3)
    assert fresh_device.stats.kernels_launched == 1
    assert fresh_device.stats.total_blocks == grid
    assert fresh_device.stats.total_threads == grid * block_size
    # Work should spread over many SMs.
    active = sum(1 for sm in fresh_device.sms if sm.stats.blocks_executed > 0)
    assert active > 1


def test_block_too_large_raises(fresh_device):
    @launch(grid=1, block=4096)
    def bad(ctx):
        pass

    with pytest.raises(ValueError):
        bad()
