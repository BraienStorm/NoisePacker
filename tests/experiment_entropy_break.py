import os
import gzip
import numpy as np
import time
import sys

# Ensure src can be imported
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.compressor import NoisePacker
from src.config import *
from src.prngs import PRNG_REGISTRY

def main():
    print("=== ENTROPY BREAKING EXPERIMENT (STAGGERED) ===")
    print("Goal: Prove that XORing noise with best-fit seeds reduces entropy.")
    print(f"Configuration: Radius={SEARCH_RADIUS}, Algos={len(PRNG_REGISTRY)}")

    # 1. Generate Data (5KB)
    TOTAL_BYTES = 5 * 1024
    raw_data = os.urandom(TOTAL_BYTES)

    # 2. Baseline Compression
    gzip_raw = gzip.compress(raw_data)
    print(f"Original Size:   {len(raw_data)} bytes")
    print(f"GZIP(Original):  {len(gzip_raw)} bytes")
    print("-" * 40)

    # 3. Transform
    packer = NoisePacker()

    chunk_len_bytes = (BLOCKS_PER_CHUNK * BLOCK_SIZE) // 8
    n_chunks = len(raw_data) // chunk_len_bytes
    chunk_len_bits = BLOCKS_PER_CHUNK * BLOCK_SIZE

    transformed_payload = bytearray()
    metadata = bytearray()

    print(f"Processing {n_chunks} chunks...")
    start_t = time.time()

    total_zeros = 0
    total_bits = 0

    for i in range(n_chunks):
        chunk_bytes = raw_data[i*chunk_len_bytes : (i+1)*chunk_len_bytes]
        chunk_int = int.from_bytes(chunk_bytes, 'big')

        # Use the new explicit transformation method
        seed, prng_id, residual_int, ratio, polarity = packer.scan_for_best_transformation(chunk_int, chunk_len_bits)

        # Append Residual
        res_bytes = residual_int.to_bytes(chunk_len_bytes, 'big')
        transformed_payload.extend(res_bytes)

        # Metadata (Simulated cost: 2 bytes)
        metadata.extend(b'XX')

        total_zeros += (chunk_len_bytes*8) * ratio
        total_bits += (chunk_len_bytes*8)

        if i % 5 == 0:
            print(f"Chunk {i}: Best Ratio {ratio:.2f}")

    duration = time.time() - start_t

    # 4. Compress Transformed Payload
    gzip_transformed = gzip.compress(transformed_payload)

    print("-" * 40)
    print(f"Transformation Time: {duration:.2f}s")
    print(f"Avg Zero Ratio:      {total_zeros/total_bits*100:.2f}% (Target > 50%)")
    print("-" * 40)
    print(f"Transformed Size:    {len(transformed_payload)} bytes")
    print(f"GZIP(Transformed):   {len(gzip_transformed)} bytes")

    total_new_size = len(gzip_transformed) + len(metadata)
    print(f"TOTAL (Meta + GZ):   {total_new_size} bytes")

    diff = len(raw_data) - total_new_size
    print("-" * 40)
    if diff > 0:
        print(f"🏆 SUCCESS! Reduced by {diff} bytes ({diff/len(raw_data)*100:.2f}%)")
    else:
        print(f"💀 FAIL. Increased by {abs(diff)} bytes.")
        gz_diff = len(gzip_raw) - len(gzip_transformed)
        if gz_diff > 0:
             print(f"Partial Success: GZIP compressed the transformed data {gz_diff} bytes better than original.")

if __name__ == "__main__":
    main()