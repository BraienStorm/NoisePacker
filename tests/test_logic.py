import unittest
import random
import numpy as np
from src.compressor import NoisePacker
from src.config import *
from src.prngs import PRNG_REGISTRY

class TestNoisePacker(unittest.TestCase):
    def test_find_exact_seed_xorshift(self):
        """Test if Packer finds a hidden Xorshift32 seed in Dimension 0."""
        packer = NoisePacker()
        packer.current_seed = 500

        # Dim 0 is index 0
        prng = PRNG_REGISTRY[0]
        target_seed = 555
        prng.seed(target_seed)

        # Create chunk
        chunk_len_bytes = (BLOCKS_PER_CHUNK * BLOCK_SIZE) // 8
        chunk_len_bits = BLOCKS_PER_CHUNK * BLOCK_SIZE
        chunk_bytes = prng.randbytes(chunk_len_bytes)

        chunk_int = int.from_bytes(chunk_bytes, 'big')
        bits_str = format(chunk_int, f'0{chunk_len_bits}b')[-chunk_len_bits:]
        flat_bits = np.array([int(b) for b in bits_str], dtype=np.uint8)
        chunk_data = flat_bits.reshape((BLOCKS_PER_CHUNK, BLOCK_SIZE))

        is_compressed, cost, delta = packer.process_chunk(chunk_data)

        self.assertTrue(is_compressed, "Packer failed to compress known Xorshift seed")
        self.assertEqual(packer.current_seed, target_seed, "Packer found wrong seed")

if __name__ == '__main__':
    unittest.main()