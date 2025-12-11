
import time
from src.compressor import NoisePacker
import numpy as np
from src.config import *

def profile_one_chunk():
    print("Profiling one chunk...")
    packer = NoisePacker()

    # Create a random chunk
    chunk_len_bits = BLOCKS_PER_CHUNK * BLOCK_SIZE
    n_bytes = (chunk_len_bits + 7) // 8

    # 3 * 512 bits = 1536 bits = 192 bytes
    chunk_bytes = np.random.bytes(n_bytes)
    chunk_bits = np.unpackbits(np.frombuffer(chunk_bytes, dtype=np.uint8))

    # Ensure shape matches what process_chunk expects (1536,)
    chunk_bits = chunk_bits[:chunk_len_bits]

    print(f"Chunk size: {len(chunk_bits)} bits")

    start_time = time.time()
    result = packer.process_chunk(chunk_bits)
    end_time = time.time()

    print(f"Result: {result}")
    print(f"Time taken: {end_time - start_time:.4f} seconds")

if __name__ == "__main__":
    profile_one_chunk()
