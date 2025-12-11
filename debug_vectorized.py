
import time
import numpy as np
from src.config import *

# Emulate the config constants if not available or for standalone test
SEARCH_RADIUS = 16384
BLOCK_SIZE = 512
BLOCKS_PER_CHUNK = 3
CHUNK_LEN_BITS = BLOCKS_PER_CHUNK * BLOCK_SIZE
N_BYTES = (CHUNK_LEN_BITS + 7) // 8

def vectorized_hunter(chunk_bytes, current_seed, dim_offset):
    # 1. Generate Candidates
    r = np.arange(1, SEARCH_RADIUS, dtype=np.int64)
    offsets = np.concatenate(([0], np.column_stack((r, -r)).flatten()))

    # candidates
    candidates = np.abs(current_seed + offsets)

    # Apply dimension offset
    states = (candidates + dim_offset) & 0xFFFFFFFF
    states[states == 0] = 1
    states = states.astype(np.uint32)

    # Pre-compute bit counts lookup
    BIT_COUNTS = np.array([bin(x).count('1') for x in range(256)], dtype=np.uint8)

    # Chunk bytes as array
    chunk_arr = np.frombuffer(chunk_bytes, dtype=np.uint8)

    total_diffs = np.zeros(len(states), dtype=np.uint32)

    for i in range(N_BYTES):
        states ^= (states << 13)
        states ^= (states >> 17)
        states ^= (states << 5)

        mask_byte = states & 0xFF
        diff = mask_byte ^ chunk_arr[i]
        total_diffs += BIT_COUNTS[diff]

    zeros = CHUNK_LEN_BITS - total_diffs
    effective_zeros = np.maximum(zeros, total_diffs)
    best_idx = np.argmax(effective_zeros)
    best_val = effective_zeros[best_idx]

    return best_val / CHUNK_LEN_BITS

def profile_vectorized():
    print("Profiling Vectorized Hunter...")

    # Random chunk
    chunk_bytes = np.random.bytes(N_BYTES)

    start = time.time()
    best_ratio = vectorized_hunter(chunk_bytes, 1000, 0)
    end = time.time()

    print(f"Best Ratio: {best_ratio}")
    print(f"Time: {end - start:.4f} seconds")

if __name__ == "__main__":
    profile_vectorized()
