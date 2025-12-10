import numpy as np

# Pre-compute bit count table for fast vectorized counting
BIT_COUNTS = np.array([bin(x).count('1') for x in range(256)], dtype=np.uint8)

class PRNG:
    def seed(self, seed_val):
        pass
    def randbytes(self, n):
        pass
    def batch_search(self, chunk_arr, current_seed, search_offsets):
        """
        Optional vectorized search. Returns (best_ratio, best_candidate, best_offset) or None.
        """
        return None

class Xorshift32(PRNG):
    """
    Simple 32-bit Xorshift. Very fast.
    Supports 'Dimensional Shifting' via offset in constructor.
    """
    def __init__(self, dimension_offset=0):
        self.state = 1 # Cannot be 0
        self.offset = dimension_offset

    def seed(self, seed_val):
        # Apply dimensional offset to map the same seed integer to a different state space
        self.state = (seed_val + self.offset) & 0xFFFFFFFF
        if self.state == 0:
            self.state = 1

    def randbytes(self, n):
        output = bytearray(n)
        x = self.state
        for i in range(n):
            x ^= (x << 13) & 0xFFFFFFFF
            x ^= (x >> 17)
            x ^= (x << 5) & 0xFFFFFFFF
            output[i] = x & 0xFF

        self.state = x
        return bytes(output)

    def batch_search(self, chunk_arr, current_seed, search_offsets, chunk_len_bits):
        """
        Vectorized search for Xorshift32.
        """
        n_bytes = len(chunk_arr)

        # Calculate candidates
        candidates = np.abs(current_seed + search_offsets)

        # Apply dimensional offset
        states = (candidates + self.offset) & 0xFFFFFFFF
        states[states == 0] = 1
        states = states.astype(np.uint32)

        total_diffs = np.zeros(len(states), dtype=np.uint32)

        # Xorshift loop (vectorized)
        for i in range(n_bytes):
            states ^= (states << 13)
            states ^= (states >> 17)
            states ^= (states << 5)

            mask_byte = states & 0xFF
            diff = mask_byte ^ chunk_arr[i]
            total_diffs += BIT_COUNTS[diff]

        # Calculate ratios
        zeros = chunk_len_bits - total_diffs
        effective_zeros = np.maximum(zeros, total_diffs)
        ratios = effective_zeros / chunk_len_bits

        # Find best
        max_idx = np.argmax(ratios)
        best_ratio = ratios[max_idx]
        best_offset = search_offsets[max_idx]
        best_candidate = candidates[max_idx]

        # Also return polarity for scan_for_best_transformation
        # If total_diffs > zeros, it's inverted (polarity 1)
        # diffs > chunk_len_bits - diffs => 2*diffs > len => diffs > len/2
        best_polarity = 1 if total_diffs[max_idx] > zeros[max_idx] else 0

        return best_ratio, best_candidate, best_offset, best_polarity

# Registry: 3 Dimensions of Xorshift32 (0, 1, 2)
# User requested 3 dimensions to allow optimized signaling (0=Stay, 1x=Switch).
PRNG_REGISTRY = [
    Xorshift32(dimension_offset=0),            # Dim 0
    Xorshift32(dimension_offset=0x55555555),   # Dim 1 (+1.3G)
    Xorshift32(dimension_offset=0xAAAAAAAA),   # Dim 2 (+2.6G)
]