import math
from src.config import BLOCK_SIZE

def calculate_entropy_cost(ratio, size):
    """
    Calculates the theoretical size limit (Shannon entropy) for a given ratio of zeros.
    """
    if ratio == 0:
        return 0
    if ratio == 1:
        return 0
    if ratio == 0.5:
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
