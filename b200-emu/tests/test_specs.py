from b200_emu.specs import B200


def test_b200_shape():
    assert B200.num_sms == 208
    assert B200.num_tensor_cores == 832
    assert B200.threads_per_warp == 32
    assert B200.hbm_capacity_bytes == 192 * 1024**3
    assert B200.peak_fp8_tflops == 10_000.0


def test_describe_is_multiline():
    text = B200.describe()
    assert "B200" in text
    assert "HBM3e" in text
    assert text.count("\n") >= 8
