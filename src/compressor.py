import numpy as np
import random
from src.config import *
from src.utils import *

class NoisePacker:
    def __init__(self):
        print("Initializing NoisePacker Engine...")
        # self.masks table is no longer needed for direct PRNG generation
        self.current_seed = 0
        
        # Statistics
        self.stats = {
            "total_bits_in": 0,
            "total_bits_out": 0,
            "chunks_processed": 0,
            "chunks_compressed": 0,
            "chunks_raw": 0
        }

    def process_chunk(self, chunk_data):
        """
        Processes a single chunk (consisting of multiple blocks).
        Decides whether to Compress (Seed) or keep Raw (Bitmap Flag).
        """
        chunk_len_bits = BLOCKS_PER_CHUNK * BLOCK_SIZE
        
        # Convert chunk_data (numpy bits) to a single integer for fast bitwise ops
        # chunk_data is (BLOCKS_PER_CHUNK, BLOCK_SIZE) of 0s and 1s.
        # We flatten it to a 1D array of bits, then pack to bytes, then to int.
        # Note: np.packbits packs 8 bits into a byte.
        flat_bits = chunk_data.flatten()
        packed_bytes = np.packbits(flat_bits).tobytes()
        chunk_int = int.from_bytes(packed_bytes, 'big')

        # 1. Calculate Raw Cost (Original + 1 bit Flag)
        cost_raw = chunk_len_bits + 1
        
        # 2. Hunt for a better Seed
        found, best_seed, delta, best_ratio = self._lazy_hunter(chunk_int, chunk_len_bits)
        
        if found:
            # Calculate Compressed Cost
            # Cost = Flag(1) + Delta(VLC) + Polarity(1) + EntropyPayload
            header_cost = 1 + calculate_delta_cost(delta) + 1
            payload_cost = calculate_entropy_cost(best_ratio, chunk_len_bits)
            
            cost_compressed = header_cost + payload_cost
            
            if cost_compressed < cost_raw:
                # SUCCESS: We compress!
                self.current_seed = best_seed
                self.stats["total_bits_out"] += cost_compressed
                self.stats["chunks_compressed"] += 1
                return True, cost_compressed, delta
                
        # FAILURE: Keep raw
        self.stats["total_bits_out"] += cost_raw
        self.stats["chunks_raw"] += 1
        return False, cost_raw, 0

    def _lazy_hunter(self, chunk_int, chunk_len_bits):
        """
        Searches for a seed in the vicinity of the current_seed.
        Using direct PRNG masking (random.seed -> random.randbytes).
        """
        # Calculate how many bytes we need
        n_bytes = (chunk_len_bits + 7) // 8

        # Use a local Random instance to avoid polluting global state
        rng = random.Random()

        best_candidate = 0
        best_offset = 0
        best_ratio = 0.5
        found_any = False

        for d in range(SEARCH_RADIUS):
            # Check +d and -d
            offsets = [d] if d == 0 else [d, -d]
            
            for offset in offsets:
                candidate = abs(self.current_seed + offset)
                
                # Generate mask from candidate seed
                rng.seed(candidate)
                mask_bytes = rng.randbytes(n_bytes)
                mask_int = int.from_bytes(mask_bytes, 'big')

                # XOR and count zeros
                xor_val = chunk_int ^ mask_int

                # Count ones (differences)
                diffs = xor_val.bit_count()
                
                # Symmetry logic
                zeros = chunk_len_bits - diffs
                effective_zeros = max(zeros, diffs)
                
                ratio = effective_zeros / chunk_len_bits

                if ratio > best_ratio:
                    best_ratio = ratio
                    best_candidate = candidate
                    best_offset = offset
                    found_any = True

                    # Optimization: If we find a "perfect" or near-perfect match, stop early.
                    # 0.99 is effectively perfect for this purpose.
                    if best_ratio > 0.99:
                        return True, best_candidate, best_offset, best_ratio

        if found_any and best_ratio >= TARGET_RATIO:
            return True, best_candidate, best_offset, best_ratio
                    
        return False, 0, 0, 0.5