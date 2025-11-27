import numpy as np
import os
from src.config import *
from src.utils import *

class NoisePacker:
    def __init__(self):
        print("Initializing NoisePacker Engine...")
        self.masks = generate_masks_table()
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
        
        # 1. Calculate Raw Cost (Original + 1 bit Flag)
        cost_raw = chunk_len_bits + 1
        
        # 2. Hunt for a better Seed
        found, best_seed, delta, best_ratio = self._lazy_hunter(chunk_data)
        
        if found:
            # Calculate Compressed Cost
            # Cost = Flag(1) + Delta(VLC) + EntropyPayload
            header_cost = 1 + calculate_delta_cost(delta)
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

    def _lazy_hunter(self, chunk_data):
        """
        Searches for a seed in the vicinity of the current_seed.
        """
        for d in range(SEARCH_RADIUS):
            # Check +d and -d
            offsets = [d] if d == 0 else [d, -d]
            
            for offset in offsets:
                candidate = abs(self.current_seed + offset)
                
                # Generate masks from candidate seed
                rng = np.random.RandomState(candidate)
                gen_mask_ids = rng.randint(0, 256, size=BLOCKS_PER_CHUNK)
                
                total_zeros = 0
                
                # Check match for all blocks in this chunk
                for b in range(BLOCKS_PER_CHUNK):
                    mask = self.masks[gen_mask_ids[b]]
                    # XOR and count zeros
                    z = np.sum(np.bitwise_xor(chunk_data[b], mask) == 0)
                    # Invert if ones are majority (symmetry)
                    if z < BLOCK_SIZE / 2: 
                        z = BLOCK_SIZE - z
                    total_zeros += z
                
                ratio = total_zeros / (BLOCKS_PER_CHUNK * BLOCK_SIZE)
                
                # If ratio is good enough AND worth the delta cost
                if ratio >= TARGET_RATIO:
                    # Quick check: Does the gain cover the delta cost?
                    # (Approximate check to save time)
                    return True, candidate, offset, ratio
                    
        return False, 0, 0, 0.5