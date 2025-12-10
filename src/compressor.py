import numpy as np
import random
from src.config import *
from src.utils import *
from src.prngs import PRNG_REGISTRY

class NoisePacker:
    def __init__(self):
        print("Initializing NoisePacker Engine...")
        self.current_seed = 0
        
        # PRNG_REGISTRY now contains instances of Xorshift32 with different offsets
        self.prng_instances = PRNG_REGISTRY

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
        
        flat_bits = chunk_data.flatten()
        packed_bytes = np.packbits(flat_bits).tobytes()
        chunk_int = int.from_bytes(packed_bytes, 'big')

        # 1. Calculate Raw Cost (Original + 1 bit Flag)
        cost_raw = chunk_len_bits + 1
        
        # 2. Hunt for a better Seed
        found, best_seed, delta, best_ratio, best_prng_id = self._lazy_hunter(chunk_int, chunk_len_bits)
        
        if found:
            # Calculate Compressed Cost
            # Cost = Flag(1) + PRNG_ID(2) + Delta(VLC) + Polarity(1) + EntropyPayload
            # We assume PRNG_ID takes 2 bits (since we have 3 types, fits in 2 bits)
            header_cost = 1 + 2 + calculate_delta_cost(delta) + 1
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
        Searches for a seed across multiple PRNGs.
        """
        n_bytes = (chunk_len_bits + 7) // 8

        best_candidate = 0
        best_offset = 0
        best_ratio = 0.5
        best_prng_id = 0
        found_any = False

        # Iterate over all registered PRNGs
        # Note: Dimensional shifting is now handled inside the PRNG class seed() method.
        # We just search [Base-R, Base+R] for each dimension.

        for prng_id, rng in enumerate(self.prng_instances):
            for d in range(SEARCH_RADIUS):
                offsets = [d] if d == 0 else [d, -d]
                
                for offset in offsets:
                    candidate = abs(self.current_seed + offset)

                    rng.seed(candidate)
                    mask_bytes = rng.randbytes(n_bytes)
                    mask_int = int.from_bytes(mask_bytes, 'big')

                    xor_val = chunk_int ^ mask_int
                    diffs = xor_val.bit_count()

                    # Symmetry
                    zeros = chunk_len_bits - diffs
                    effective_zeros = max(zeros, diffs)

                    ratio = effective_zeros / chunk_len_bits

                    if ratio > best_ratio:
                        best_ratio = ratio
                        best_candidate = candidate
                        best_offset = offset
                        best_prng_id = prng_id
                        found_any = True

                        if best_ratio > 0.99:
                            return True, best_candidate, best_offset, best_ratio, best_prng_id

        if found_any and best_ratio >= TARGET_RATIO:
            return True, best_candidate, best_offset, best_ratio, best_prng_id

        return False, 0, 0, 0.5, 0

    def scan_for_best_transformation(self, chunk_int, chunk_len_bits):
        """
        Scans all PRNGs and seeds within SEARCH_RADIUS to find the absolute best
        XOR mask that maximizes the number of zeros (entropy breaking).
        Returns: best_seed, best_prng_id, best_xor_val, best_ratio, best_polarity
        """
        n_bytes = (chunk_len_bits + 7) // 8
        best_candidate = 0
        best_ratio = -1.0
        best_prng_id = 0
        best_xor_val = 0
        best_polarity = 0 # 0: Normal, 1: Inverted

        for prng_id, rng_inst in enumerate(self.prng_instances):
            for d in range(SEARCH_RADIUS):
                offsets = [d] if d == 0 else [d, -d]
                for offset in offsets:
                    candidate = abs(self.current_seed + offset)
                    rng_inst.seed(candidate)
                    mask_bytes = rng_inst.randbytes(n_bytes)
                    mask_int = int.from_bytes(mask_bytes, 'big')

                    xor_val = chunk_int ^ mask_int
                    diffs = xor_val.bit_count()

                    # Logic for polarity
                    zeros = chunk_len_bits - diffs

                    # Check Normal
                    if (zeros / chunk_len_bits) > best_ratio:
                        best_ratio = zeros / chunk_len_bits
                        best_candidate = candidate
                        best_prng_id = prng_id
                        best_xor_val = xor_val
                        best_polarity = 0

                    # Check Inverted (Polarity)
                    if (diffs / chunk_len_bits) > best_ratio:
                         best_ratio = diffs / chunk_len_bits
                         best_candidate = candidate
                         best_prng_id = prng_id
                         # Inverted residual
                         all_ones = (1 << chunk_len_bits) - 1
                         best_xor_val = xor_val ^ all_ones
                         best_polarity = 1

        # Update current seed for next hunt
        self.current_seed = best_candidate

        return best_candidate, best_prng_id, best_xor_val, best_ratio, best_polarity