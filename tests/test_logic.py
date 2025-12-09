import unittest
import random
import numpy as np
from src.compressor import NoisePacker
from src.config import *
from src.prngs import PRNG_REGISTRY

class TestNoisePacker(unittest.TestCase):
    def test_find_exact_seed_mt(self):
        """Test if Packer finds a hidden Mersenne Twister seed."""
        packer = NoisePacker()
        packer.current_seed = 500

        target_seed = 555
        rng = random.Random(target_seed)

        # Create chunk
        chunk_len_bytes = (BLOCKS_PER_CHUNK * BLOCK_SIZE) // 8
        chunk_len_bits = BLOCKS_PER_CHUNK * BLOCK_SIZE
        chunk_bytes = rng.randbytes(chunk_len_bytes)

        chunk_int = int.from_bytes(chunk_bytes, 'big')
        bits_str = format(chunk_int, f'0{chunk_len_bits}b')[-chunk_len_bits:]
        flat_bits = np.array([int(b) for b in bits_str], dtype=np.uint8)
        chunk_data = flat_bits.reshape((BLOCKS_PER_CHUNK, BLOCK_SIZE))

        is_compressed, cost, delta = packer.process_chunk(chunk_data)

        self.assertTrue(is_compressed, "Packer failed to compress known MT seed")
        self.assertEqual(packer.current_seed, target_seed, "Packer found wrong seed")

    def test_find_exact_seed_lcg(self):
        """Test if Packer finds a hidden LCG seed."""
        packer = NoisePacker()
        packer.current_seed = 500

        # LCG is PRNG index 1
        lcg = PRNG_REGISTRY[1]()
        target_seed = 600
        lcg.seed(target_seed)

        chunk_len_bytes = (BLOCKS_PER_CHUNK * BLOCK_SIZE) // 8
        chunk_len_bits = BLOCKS_PER_CHUNK * BLOCK_SIZE
        chunk_bytes = lcg.randbytes(chunk_len_bytes)

        chunk_int = int.from_bytes(chunk_bytes, 'big')
        bits_str = format(chunk_int, f'0{chunk_len_bits}b')[-chunk_len_bits:]
        flat_bits = np.array([int(b) for b in bits_str], dtype=np.uint8)
        chunk_data = flat_bits.reshape((BLOCKS_PER_CHUNK, BLOCK_SIZE))

        is_compressed, cost, delta = packer.process_chunk(chunk_data)

        self.assertTrue(is_compressed, "Packer failed to compress known LCG seed")
        # Cannot strictly assert packer.current_seed == target_seed because collision is possible,
        # but very unlikely for this setup.
        self.assertEqual(packer.current_seed, target_seed)

if __name__ == '__main__':
    unittest.main()