# 🎲 NoisePacker — Entropy Mining Compression (PoC)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![Status](https://img.shields.io/badge/status-Release%20Candidate-green.svg)]()

> **"Random noise cannot be compressed."** — *Shannon's Source Coding Theorem*  
> **"Hold my CPU cycles."** — *NoisePacker*

**NoisePacker** is an experimental **asymmetric** compression tool that tries to squeeze *finite* chunks of **random data** (e.g. `os.urandom`, pseudo-random streams).
It uses a **"Transformation & Residual"** approach: instead of compressing the data directly, it mines for a PRNG seed that generates a similar bitstream, XORs them to create a low-entropy "residual," and compresses that residual.

> ⚠️ **Research/PoC:** Works best on pseudo-random data. On true randomness, gain is marginal (~1%).

---

## ✨ Key features

- **Entropy Mining:** Brute-force search for PRNG seeds (Xorshift32) that produce a matching mask.
- **4-Dimensional Shifting:** Uses 4 disjoint state spaces of the Xorshift algorithm to maximize coverage without overlap.
- **Transformation Strategy:** `Data XOR Seed_Stream = Low_Entropy_Residual`.
- **Hybrid Compression:** Compresses the residual using **ZLIB** (Deflate).
- **.nsp File Format:** Custom binary format storing Metadata (Flags, Deltas) + Compressed Residuals.
- **Lossless:** Fully reversible. Checks polarity (inverted masks) to ensure optimal matching.

---

## 🧠 How it works

1. **Chunking:** Split input into fixed blocks (1536 bits).
2. **Mining:** For each block, scan 16,384 seeds across 4 Dimensions of Xorshift32.
3. **Selection:** Pick the seed/dimension that maximizes zeros (or ones) in the XOR difference.
4. **Encoding:**
   - Store **Seed Delta** (difference from previous seed).
   - Store **Dimension ID** (using "Sticky" optimization: 0 bit if unchanged).
   - Compress the **Residual** stream with ZLIB.

---

## 📊 Performance

- **Pseudo-Random Data:** Near perfect compression (~1-2% of original size).
- **True Random Data:** ~1% compression (verified on 5KB `os.urandom` samples).
- **Speed:** Optimized bitwise Python implementation. ~3-4 minutes for 50KB with deep search radius.

---

## ✅ Installation

### Prerequisites
- Python **3.10+** (Required for `int.bit_count` and `random.randbytes`)
- NumPy

### Setup

```bash
git clone https://github.com/YOUR_USERNAME/NoisePacker.git
cd NoisePacker
pip install -r requirements.txt
```

---

## ▶️ Usage

### Compress a file
```python
from src.file_io import NoisePackerFile

packer = NoisePackerFile()
packer.compress_file("input.bin", "compressed.nsp")
```

### Decompress a file
```python
packer.decompress_file("compressed.nsp", "restored.bin")
```

### Run Benchmark
```bash
python run_benchmark.py
```

---

## 🗺️ Roadmap

- [x] **v1.0** Brute-force seed search
- [x] **v2.0** Differential seed coding
- [x] **v3.0** Multi-Algo Mining (Mersenne, LCG, Xorshift)
- [x] **v4.0** 4-Dimensional Xorshift32 & File I/O (.nsp)
- [ ] **v5.0** GPU acceleration (CUDA) for massive search radius

---

## 📜 License

Distributed under the **MIT License**. See `LICENSE` for details.

## 👤 Author

**[Pásthi Dániel]**
- 💻 GitHub: [@BraienStorm](https://github.com/BraienStorm)

---