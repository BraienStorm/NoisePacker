# Configuration for NoisePacker

# The size of a single atomic block (in bits)
BLOCK_SIZE = 512

# How many blocks to group together for a single Seed Search
# 3 blocks = 1536 bits (found to be optimal in experiments)
BLOCKS_PER_CHUNK = 3

# The "Lazy Hunter" radius. How far do we search for a seed?
# Larger radius = better compression but slower speed.
# 8000 was found to be a sweet spot for positive gain.
SEARCH_RADIUS = 8000

# Target Ratio to consider "Good enough" (e.g. 0.525 = 52.5% zeros)
TARGET_RATIO = 0.525