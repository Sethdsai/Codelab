import numpy as np
import pytest

from b200_emu.tensor_core import DType, TensorCoreStats, tensor_core_mma


@pytest.mark.parametrize("dtype", [DType.BF16, DType.FP16, DType.TF32, DType.FP32])
def test_mma_matches_numpy_closely(dtype):
    rng = np.random.default_rng(0)
    a = rng.standard_normal((64, 128)).astype(np.float32)
    b = rng.standard_normal((128, 32)).astype(np.float32)
    stats = TensorCoreStats()
    d = tensor_core_mma(a, b, in_dtype=dtype, stats=stats)
    ref = a.astype(np.float32) @ b.astype(np.float32)
    tol = {
        DType.FP32: 1e-4,
        DType.TF32: 5e-3,
        DType.BF16: 5e-2,
        DType.FP16: 1e-2,
    }[dtype]
    assert d.shape == ref.shape
    np.testing.assert_allclose(d, ref, rtol=tol, atol=tol * np.abs(ref).mean())
    assert stats.mma_ops == 1
    assert stats.flops == 2 * 64 * 32 * 128


def test_mma_with_bias():
    rng = np.random.default_rng(1)
    a = rng.standard_normal((16, 32)).astype(np.float32)
    b = rng.standard_normal((32, 8)).astype(np.float32)
    c = rng.standard_normal((16, 8)).astype(np.float32)
    d = tensor_core_mma(a, b, c, in_dtype=DType.FP32)
    np.testing.assert_allclose(d, a @ b + c, rtol=1e-4, atol=1e-4)


def test_mma_shape_mismatch():
    a = np.zeros((4, 5), dtype=np.float32)
    b = np.zeros((6, 7), dtype=np.float32)
    with pytest.raises(ValueError):
        tensor_core_mma(a, b)


def test_fp8_e4m3_is_lossy_but_correct_direction():
    rng = np.random.default_rng(2)
    a = rng.standard_normal((32, 64)).astype(np.float32)
    b = rng.standard_normal((64, 32)).astype(np.float32)
    d_fp8 = tensor_core_mma(a, b, in_dtype=DType.FP8_E4M3)
    d_fp32 = a @ b
    # FP8 should be noisier than FP32, but still strongly correlated.
    corr = np.corrcoef(d_fp8.ravel(), d_fp32.ravel())[0, 1]
    assert corr > 0.95
