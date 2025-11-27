# 🎲 NoisePacker — Entropy Mining Compression (PoC)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/)
[![Status](https://img.shields.io/badge/status-Proof%20of%20Concept-red.svg)]()

> **"Random noise cannot be compressed."** — *Shannon's Source Coding Theorem*  
> **"Hold my CPU cycles."** — *NoisePacker*

**NoisePacker** is an experimental **asymmetric** compression concept that tries to squeeze *finite* chunks of **cryptographically strong random data** (e.g. `os.urandom`, encrypted blobs).  
Instead of finding patterns (ZIP/LZ/LZMA), it “mines” for **generators**: PRNG states (seeds) that statistically correlate with local fluctuations and let us reduce entropy *within a block*.

> ⚠️ **Research/PoC:** Don’t use this for important or archival storage.

---

## ✨ Key ideas / features

- **Entropy mining:** brute-force search for PRNG seeds that produce a “useful” mask for a block.
- **Lazy Hunter:** adjacent optimal seeds often cluster → store **deltas** efficiently with variable-length coding.
- **Bitmap fallback:** 1 bit / block to mark **raw vs packed**, so the format stays robust when mining fails.
- **Asymmetric design:** **very slow compression** (mining) → **fast decompression** (generation + decode).

---

## 🧠 How it works (high level)

Conventional theory says **max-entropy streams** are incompressible — which is true in the limit of infinite data.  
For **finite blocks** (e.g. 512 bits), randomness still exhibits **local statistical fluctuations**. NoisePacker trades **compute time** for **a tiny probability of gain**.

### Pipeline

1. **Chunking**  
   Split data into fixed-size blocks (e.g. 512 bits).

2. **Seed mining (brute force)**  
   For each block, simulate many PRNG states (currently **Mersenne Twister**) and search for a generated bitstream that acts like a “good XOR mask” and reduces block entropy.

3. **Differential seed coding**  
   - Storing a full seed each time is too expensive (≈32 bits baseline).
   - Observation: nearby blocks often have nearby “good” seeds.
   - Store **Δ(seed)** using **variable-length coding**.

4. **Economic decision**  
   Compress a block only if:

   `entropy_gain > delta_cost + 1_bit_flag`

   Otherwise store the block raw.

---

## 📊 Example benchmark

Tested on **50 KB of `os.urandom`** (high-quality kernel entropy):

```text
--- NOISEPACKER BENCHMARK ---
Source: os.urandom (Cryptographic Entropy)
Size: 51200 bytes (266 chunks)
------------------------------------------------------------
...
#240   | ✅ COMP   | +1        | +0.0
#250   | ✅ COMP   | -5        | -0.9
#260   | ✅ COMP   | -2        | -0.5
------------------------------------------------------------
Execution Time: 1.51s
Chunks Compressed: 156 / 266 (58.6%)
------------------------------------------------------------
ORIGINAL SIZE: 408576 bits
PACKED SIZE:   408519 bits
------------------------------------------------------------
🏆 SUCCESS! Reduced entropy by 57 bits.
   Compression Ratio: 0.0140%
```

0.014% is tiny — but achieving *any* positive result on true random data demonstrates the **finite-block anomaly exploitation** + **Lazy Hunter** approach.

---

## ✅ Installation

### Prerequisites
- Python **3.8+**
- NumPy

### Setup

```bash
git clone https://github.com/YOUR_USERNAME/NoisePacker.git
cd NoisePacker
pip install -r requirements.txt
```

---

## ▶️ Usage

Run the included benchmark on your machine’s entropy source:

```bash
python run_benchmark.py
```

---

## 🗺️ Roadmap

- [x] **v1.0** Brute-force seed search (negative gain)
- [x] **v2.0** Differential seed coding (break-even)
- [x] **v3.0** Bitmap flagging & Lazy Hunter (positive gain)
- [ ] **v4.0** GPU acceleration (CUDA) for deeper mining
- [ ] **v5.0** Neural seed prediction?

---

## 📜 License

Distributed under the **MIT License**. See `LICENSE` for details.

---

## ⚠️ Disclaimer

This is a research experiment. Compression ratio depends heavily on luck (finding matching seeds within the search radius), parameters, and block size. It is **not** intended for critical data storage.
