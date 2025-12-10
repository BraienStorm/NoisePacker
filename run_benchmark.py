import os
import numpy as np
import time
from src.config import *
from src.compressor import NoisePacker

def main():
    # 1. Setup Data (Real Entropy)
    # 50 KB is enough for PoC
    TOTAL_BYTES = 50 * 1024 
    total_bits = TOTAL_BYTES * 8
    n_chunks = total_bits // (BLOCKS_PER_CHUNK * BLOCK_SIZE)
    
    print(f"--- NOISEPACKER BENCHMARK ---")
    print(f"Source: os.urandom (Cryptographic Entropy)")
    print(f"Size: {TOTAL_BYTES} bytes ({n_chunks} chunks)")
    print("-" * 60)
    
    # Generate Data
    raw_bytes = os.urandom(TOTAL_BYTES)
    raw_bits = np.unpackbits(np.frombuffer(raw_bytes, dtype=np.uint8))
    # Reshape to chunks
    data = raw_bits[:n_chunks * BLOCKS_PER_CHUNK * BLOCK_SIZE].reshape(
        (n_chunks, BLOCKS_PER_CHUNK, BLOCK_SIZE)
    )
    
    packer = NoisePacker()
    
    print(f"{'#ID':<5} | {'STATUS':<8} | {'RATIO':<8} | {'NET GAIN'}")
    print("-" * 60)
    
    start_time = time.time()
    
    # 2. Process
    for i in range(n_chunks):
        chunk = data[i]
        is_compressed, cost, delta = packer.process_chunk(chunk)
        
        # Visual logging for significant events
        if i % 10 == 0:
            orig_cost = (BLOCKS_PER_CHUNK * BLOCK_SIZE)
            net = orig_cost - cost
            status = "✅ COMP" if is_compressed else "❌ RAW"
            d_str = f"{delta:+d}" if is_compressed else "-"
            print(f"#{i:<5} | {status:<10} | {d_str:<8} | {net:+.1f}")
            
    duration = time.time() - start_time
    
    # 3. Results
    stats = packer.stats
    orig_size = n_chunks * BLOCKS_PER_CHUNK * BLOCK_SIZE
    new_size = int(stats["total_bits_out"])
    diff = orig_size - new_size
    
    print("-" * 60)
    print(f"Execution Time: {duration:.2f}s")
    print(f"Chunks Compressed: {stats['chunks_compressed']} / {n_chunks} ({stats['chunks_compressed']/n_chunks*100:.1f}%)")
    print("-" * 60)
    print(f"ORIGINAL SIZE: {orig_size} bits")
    print(f"PACKED SIZE:   {new_size} bits")
    print("-" * 60)
    
    if diff > 0:
        print(f"🏆 SUCCESS! Reduced entropy by {diff} bits.")
        print(f"   Compression Ratio: {diff/orig_size*100:.4f}%")
    else:
        print(f"💀 FAIL. Increased size by {abs(diff)} bits.")

if __name__ == "__main__":
    main()