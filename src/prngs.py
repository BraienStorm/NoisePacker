class PRNG:
    def seed(self, seed_val):
        pass
    def randbytes(self, n):
        pass

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

# Registry: 3 Dimensions of Xorshift32 (0, 1, 2)
# User requested 3 dimensions to allow optimized signaling (0=Stay, 1x=Switch).
PRNG_REGISTRY = [
    Xorshift32(dimension_offset=0),            # Dim 0
    Xorshift32(dimension_offset=0x55555555),   # Dim 1 (+1.3G)
    Xorshift32(dimension_offset=0xAAAAAAAA),   # Dim 2 (+2.6G)
]