# b200-emu

Architecturally-faithful software emulator of an NVIDIA **Blackwell B200**–class GPU, written in Python.

> **Honest disclaimer, read this first.**
> This is a **software emulator**. It is not, and cannot be, the same as a physical B200 — any "virtual GPU" is by definition a simulation. What this project *does* give you is a model of the B200 with the right architectural shape (208 SMs, 4 warp schedulers per SM, 5th-gen tensor cores, 192 GB HBM3e, CUDA-style kernel launches) that you can actually run code on. Heavy compute (GEMM) is dispatched to host BLAS (OpenBLAS / MKL via NumPy), so it runs at host-CPU speed — many orders of magnitude slower than a real B200, but fast enough to train small models, benchmark dtypes, and learn the architecture.

## What you get

- **`B200Device`** — 208 SMs, 832 tensor cores, 60 MB L2, 192 GB HBM3e (logical), NVLink-5, public peak-throughput numbers (20 PFLOPS FP4, 10 PFLOPS FP8, 5 PFLOPS BF16, …).
- **Memory hierarchy** — HBM3e global allocator, per-SM 228 KB unified L1/shared memory, register-file accounting, traffic stats.
- **SM / warp scheduler** — 4 warp schedulers per SM, 32-thread warps, cycle + instruction accounting.
- **5th-gen tensor cores** — warp-group MMA with FP8 (E4M3, E5M2), FP16, BF16, TF32, FP32, FP64. Low-precision inputs are properly quantized (E4M3 has max 448, round-to-nearest-even at mantissa resolution, etc.), then multiplied via BLAS with FP32 accumulate — matching Blackwell's datapath semantics.
- **CUDA-style kernel launches** — `@launch(grid, block)` decorator, `KernelContext` with grid/block/thread ids, automatic distribution across SMs.
- **Minimal NN library** — `Linear`, `ReLU`, `MLP`, cross-entropy, SGD. Every matmul flows through the tensor-core model.
- **`b200-smi` CLI** — `nvidia-smi`-style device query (text and JSON).

## Install

```bash
pip install -e ".[dev]"
```

## Quick start

```python
import numpy as np
from b200_emu import get_device, to_device, to_host
from b200_emu.kernel import launch

dev = get_device()
print(dev.spec.describe())

a = to_device(np.arange(1024, dtype=np.float32))
b = to_device(np.arange(1024, dtype=np.float32) * 2)
c = to_device(np.zeros(1024, dtype=np.float32))

@launch(grid=4, block=256)
def vadd(ctx, a, b, c):
    tid = ctx.global_thread_ids(axis=0)
    c.data[tid] = a.data[tid] + b.data[tid]

vadd(a, b, c)
print(to_host(c)[:8])   # [0, 3, 6, 9, 12, 15, 18, 21]
```

## Training demo

```bash
python -m examples.train_mlp
```

Output (abridged):

```
Training on: NVIDIA B200 (emulated)
step    0  loss=2.1190  acc=11.8%
step   50  loss=1.2430  acc=64.2%
step  100  loss=0.6138  acc=85.5%
...
Tensor-core MMAs: 903
Tensor-core work: 7.56 GFLOP
```

Every linear-layer matmul in this run goes through the 5th-gen tensor-core
model with BF16 inputs and FP32 accumulate — the same datapath you'd use on a
real B200 for mixed-precision training.

## GEMM benchmark across dtypes

```bash
python -m examples.gemm_bench
```

```
  fp32           3.84 ms     0.56 TFLOPS (emu host BLAS)
  tf32           3.90 ms     0.55 TFLOPS (emu host BLAS)
  bf16           4.12 ms     0.52 TFLOPS (emu host BLAS)
  fp16           4.08 ms     0.53 TFLOPS (emu host BLAS)
  fp8_e4m3       5.21 ms     0.41 TFLOPS (emu host BLAS)
```

(Numbers are host-CPU throughput, not a B200 prediction.)

## `b200-smi`

```bash
b200-smi
```

```
NVIDIA B200  (Architecture: Blackwell, Compute 10.0)
  Dies:              2  (104 SMs/die, 208 total)
  Tensor cores:      832 (4/SM, 5th-gen)
  HBM3e:             192 GB  @ 8000 GB/s
  L2 cache:          60 MB
  SM clock (boost):  2100 MHz
  NVLink 5:          1800 GB/s
  TDP:               1000 W
  ...
[note] This is b200-emu, a software emulator — not a physical B200.
```

## What this is not

- **Not NVIDIA proprietary.** All modelled numbers come from public Blackwell disclosures (whitepaper, GTC keynote, datasheets). The internal microarchitecture, scheduler heuristics, RTL, etc. of NVIDIA's actual silicon are not and cannot be reproduced here.
- **Not a real GPU.** It runs on your CPU. Real-B200 throughput (10 PFLOPS FP8) is ~10,000× your CPU's peak. If you want to train a big model, rent a real B200.
- **Not cycle-accurate.** We do rough instruction/cycle accounting for visibility, but it is not a substitute for GPGPU-Sim / Accel-Sim if you need performance prediction.

## Testing

```bash
pytest -q
ruff check .
```

## License

MIT.
