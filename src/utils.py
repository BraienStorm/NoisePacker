import math
import numpy as np
from src.config import BLOCK_SIZE

def calculate_entropy_cost(ratio, size):
    """
    Calculates the theoretical size limit (Shannon entropy) for a given ratio of zeros.
    """
    if ratio == 0.5 or ratio == 0 or ratio == 1:
        return size
        
    h = -ratio * math.log2(ratio) - (1-ratio) * math.log2(1-ratio)
    # Theoretical compressed size
    return size * h

def calculate_delta_cost(delta):
    """
    Calculates how many bits are needed to store the delta (VLC).
    0 -> 1 bit
    +/- N -> log2(N) + sign bit
    """
    if delta == 0:
        return 1
    # +1 for sign bit, log2 for value
    return math.ceil(math.log2(abs(delta))) + 2

def generate_masks_table():
    """
    Pre-calculates the 256 possible 8-bit masks extended to BLOCK_SIZE.
    """
    masks = np.zeros((256, BLOCK_SIZE), dtype=np.uint8)
    for i in range(256):
        # Create 8-bit pattern
        pattern = np.array([int(x) for x in format(i, '08b')], dtype=np.uint8)
        # Tile it to fill the block
        masks[i] = np.tile(pattern, BLOCK_SIZE // 8)
    return masks