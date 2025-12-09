import random

class PRNG:
    def seed(self, seed_val):
        pass
    def randbytes(self, n):
        pass

class MersenneTwister(PRNG):
    def __init__(self):
        self.rng = random.Random()

    def seed(self, seed_val):
        self.rng.seed(seed_val)

    def randbytes(self, n):
        return self.rng.randbytes(n)

class LCG(PRNG):
    """
    Linear Congruential Generator
    Using glibc constants: a = 1103515245, c = 12345, m = 2^31
    """
    def __init__(self):
        self.state = 0
        self.a = 1103515245
        self.c = 12345
        self.m = 2**31

    def seed(self, seed_val):
        self.state = seed_val & 0xFFFFFFFF

    def randbytes(self, n):
        # Generating bytes in pure Python is slower than C-module random.randbytes.
        # We optimize by generating chunks or just iterating.
        # For LCG, we output the high 8 bits of the state as a byte (better randomness).

        output = bytearray(n)
        s = self.state
        a = self.a
        c = self.c
        m = self.m

        for i in range(n):
            s = (a * s + c) % m
            # Use bits 23..30 (highest 8 bits of 31-bit result usually have best entropy)
            output[i] = (s >> 23) & 0xFF

        self.state = s
        return bytes(output)

class Xorshift32(PRNG):
    """
    Simple 32-bit Xorshift. Very fast.
    """
    def __init__(self):
        self.state = 1 # Cannot be 0

    def seed(self, seed_val):
        self.state = seed_val & 0xFFFFFFFF
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

# Registry
PRNG_REGISTRY = [
    MersenneTwister, # ID 0
    LCG,             # ID 1
    Xorshift32       # ID 2
]