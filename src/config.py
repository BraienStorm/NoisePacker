# Configuration for NoisePacker

# The size of a single atomic block (in bits)
BLOCK_SIZE = 512

# How many blocks to group together for a single Seed Search
# 3 blocks = 1536 bits (found to be optimal in experiments)
BLOCKS_PER_CHUNK = 3

# The "Lazy Hunter" radius. How far do we search for a seed?
# Larger radius = better compression but slower speed.
# Adjusted to 2048 to balance the load of multiple PRNG algorithms and slower Python implementation.
SEARCH_RADIUS = 2048

# Target Ratio to consider "Good enough" (e.g. 0.525 = 52.5% zeros)
TARGET_RATIO = 0.525