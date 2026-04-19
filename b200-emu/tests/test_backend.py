import os

import numpy as np
import pytest

from b200_emu.backend import NumpyBackend, get_backend, set_backend


@pytest.fixture(autouse=True)
def reset_backend():
    set_backend(None)
    yield
    set_backend(None)


def test_numpy_backend_matmul_matches_numpy():
    bk = NumpyBackend()
    a = np.random.randn(8, 16).astype(np.float32)
    b = np.random.randn(16, 4).astype(np.float32)
    out = bk.matmul(a, b)
    np.testing.assert_allclose(out, a @ b, rtol=1e-5, atol=1e-5)


def test_env_var_forces_numpy(monkeypatch):
    monkeypatch.setenv("B200_EMU_BACKEND", "numpy")
    set_backend(None)
    bk = get_backend()
    assert bk.name == "numpy"


def test_get_backend_returns_something():
    bk = get_backend()
    assert bk.name in {"numpy", "torch-cuda", "torch-mps", "torch-cpu"}
    assert isinstance(bk.device_desc, str) and bk.device_desc


def test_unknown_backend_falls_back_to_numpy(monkeypatch):
    monkeypatch.setenv("B200_EMU_BACKEND", "completely-made-up")
    set_backend(None)
    bk = get_backend()
    assert bk.name == "numpy"


def test_backend_roundtrip_via_tensor_core_mma(monkeypatch):
    monkeypatch.setenv("B200_EMU_BACKEND", "numpy")
    set_backend(None)
    from b200_emu.tensor_core import DType, tensor_core_mma

    a = np.random.randn(32, 64).astype(np.float32)
    b = np.random.randn(64, 16).astype(np.float32)
    out = tensor_core_mma(a, b, in_dtype=DType.FP32)
    np.testing.assert_allclose(out, a @ b, rtol=1e-4, atol=1e-4)


def test_torch_backend_if_available():
    """If torch is installed, the torch-cpu backend should work."""
    try:
        import torch  # noqa: F401
    except ImportError:
        pytest.skip("torch not installed")
    os.environ["B200_EMU_BACKEND"] = "torch-cpu"
    set_backend(None)
    try:
        bk = get_backend()
        # Either picked torch-cpu, or fell back to numpy if torch CPU init fails.
        assert bk.name in {"torch-cpu", "numpy"}
        a = np.random.randn(8, 8).astype(np.float32)
        b = np.random.randn(8, 8).astype(np.float32)
        out = bk.matmul(a, b)
        np.testing.assert_allclose(out, a @ b, rtol=1e-4, atol=1e-4)
    finally:
        os.environ.pop("B200_EMU_BACKEND", None)
        set_backend(None)
