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
        found, best_seed, delta, best_ratio, best_prng_id = self._lazy_hunter(packed_bytes, chunk_len_bits)
        
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

    def _lazy_hunter(self, chunk_bytes, chunk_len_bits):
        """
        Searches for a seed across multiple PRNGs using vectorized search.
        """
        n_bytes = (chunk_len_bits + 7) // 8

        # Prepare chunk data for vectorized comparison
        chunk_arr = np.frombuffer(chunk_bytes, dtype=np.uint8)

        # Generate offsets array once
        r = np.arange(1, SEARCH_RADIUS, dtype=np.int64)
        offsets = np.concatenate(([0], np.column_stack((r, -r)).flatten()))

        best_candidate_global = 0
        best_offset_global = 0
        best_ratio_global = 0.5
        best_prng_id_global = 0
        found_any_global = False

        for prng_id, rng in enumerate(self.prng_instances):
            # Check if PRNG supports vectorized search
            if hasattr(rng, 'batch_search'):
                result = rng.batch_search(chunk_arr, self.current_seed, offsets, chunk_len_bits)
                if result:
                    ratio, candidate, offset, polarity = result
                    if ratio > best_ratio_global:
                        best_ratio_global = ratio
                        best_offset_global = offset
                        best_candidate_global = candidate
                        best_prng_id_global = prng_id
                        found_any_global = True
            else:
                 # Fallback to slow loop if not supported (omitted for now as we know we use Xorshift32)
                 pass

        if found_any_global and best_ratio_global >= TARGET_RATIO:
            return True, best_candidate_global, best_offset_global, best_ratio_global, best_prng_id_global

        return False, 0, 0, 0.5, 0

    def scan_for_best_transformation(self, chunk_int, chunk_len_bits):
        """
        Scans all PRNGs and seeds within SEARCH_RADIUS to find the absolute best
        XOR mask that maximizes the number of zeros.
        """
        n_bytes = (chunk_len_bits + 7) // 8
        chunk_bytes = chunk_int.to_bytes(n_bytes, 'big')
        chunk_arr = np.frombuffer(chunk_bytes, dtype=np.uint8)

        r = np.arange(1, SEARCH_RADIUS, dtype=np.int64)
        offsets = np.concatenate(([0], np.column_stack((r, -r)).flatten()))

        best_candidate = 0
        best_ratio = -1.0
        best_prng_id = 0
        best_polarity = 0

        # Store index to reconstruct mask
        best_rng_offset = 0

        for prng_id, rng in enumerate(self.prng_instances):
            if hasattr(rng, 'batch_search'):
                result = rng.batch_search(chunk_arr, self.current_seed, offsets, chunk_len_bits)
                if result:
                    ratio, candidate, offset, polarity = result

                    if ratio > best_ratio:
                        best_ratio = ratio
                        best_candidate = candidate
                        best_prng_id = prng_id
                        best_polarity = polarity
                        best_rng_offset = rng.offset

        # Reconstruct the best XOR mask
        # We need to manually reconstruct because we need the full mask as int
        state = (best_candidate + best_rng_offset) & 0xFFFFFFFF
        if state == 0: state = 1

        mask_bytes_out = bytearray(n_bytes)
        x = state
        for i in range(n_bytes):
            x ^= (x << 13) & 0xFFFFFFFF
            x ^= (x >> 17)
            x ^= (x << 5) & 0xFFFFFFFF
            mask_bytes_out[i] = x & 0xFF

        mask_int = int.from_bytes(mask_bytes_out, 'big')

        xor_val = chunk_int ^ mask_int
        if best_polarity == 1:
            all_ones = (1 << chunk_len_bits) - 1
            xor_val ^= all_ones

        self.current_seed = best_candidate

        return best_candidate, best_prng_id, xor_val, best_ratio, best_polarity
