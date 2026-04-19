import numpy as np
import pytest

from b200_emu.device import B200Device, set_device
from b200_emu.memory import to_device, to_host


@pytest.fixture(autouse=True)
def fresh_device():
    dev = B200Device()
    set_device(dev)
    yield dev
    set_device(None)


def test_h2d_d2h_roundtrip(fresh_device):
    host = np.arange(64, dtype=np.float32).reshape(8, 8)
    d = to_device(host)
    assert d.shape == (8, 8)
    back = to_host(d)
    np.testing.assert_array_equal(back, host)
    assert fresh_device.mem_stats.hbm_bytes_written >= host.nbytes
    assert fresh_device.mem_stats.hbm_bytes_read >= host.nbytes


def test_hbm_accounting(fresh_device):
    a = to_device(np.zeros((1024, 1024), dtype=np.float32))
    assert fresh_device.hbm.used == a.nbytes
    fresh_device.hbm.free(a)
    assert fresh_device.hbm.used == 0
