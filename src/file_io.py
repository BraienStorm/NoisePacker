import zlib
import struct
import numpy as np
from src.compressor import NoisePacker
from src.config import *
from src.utils import calculate_delta_cost

MAGIC_HEADER = b'NSP1' # NoisePacker v1

class NoisePackerFile:
    def __init__(self):
        self.packer = NoisePacker()

    def compress_file(self, input_path, output_path):
        """
        Compresses input file to .nsp format.
        Structure:
        [MAGIC:4]
        [ORIGINAL_SIZE:8]
        [CHUNK_SIZE_BITS:4] (Usually 1536)
        [ZLIB_PAYLOAD: Variable]
            Sequence of:
            [METADATA (Fixed 5 bytes per chunk)] + [TRANSFORMED_RESIDUAL]
        """
        with open(input_path, 'rb') as f:
            data = f.read()

        chunk_len_bytes = (BLOCKS_PER_CHUNK * BLOCK_SIZE) // 8
        chunk_len_bits = BLOCKS_PER_CHUNK * BLOCK_SIZE

        original_len = len(data)

        # Pad data
        padded_data = data
        padding = 0
        if original_len % chunk_len_bytes != 0:
            padding = chunk_len_bytes - (original_len % chunk_len_bytes)
            padded_data += b'\x00' * padding

        n_chunks = len(padded_data) // chunk_len_bytes

        # We will concatenate Metadata + Residuals into a single stream and compress it with zlib
        # Metadata format per chunk:
        # [PRNG_ID(2 bits) | POLARITY(1 bit) | UNUSED(5 bits)] -> 1 byte
        # [SEED_DELTA(Signed Int)] -> 4 bytes (Fixed size for PoC simplicity)
        # Total: 5 bytes metadata + chunk_len_bytes residual

        stream_buffer = bytearray()

        self.packer.current_seed = 0
        last_seed = 0

        for i in range(n_chunks):
            chunk_bytes = padded_data[i*chunk_len_bytes : (i+1)*chunk_len_bytes]
            chunk_int = int.from_bytes(chunk_bytes, 'big')

            # Find best transformation
            seed, prng_id, residual_int, ratio, polarity = self.packer.scan_for_best_transformation(chunk_int, chunk_len_bits)

            # Metadata Construction
            # Byte 1: Flags
            flags = (prng_id & 0x03) | ((polarity & 0x01) << 2)
            stream_buffer.append(flags)

            # Bytes 2-5: Seed Delta (Signed 32-bit big endian)
            # Delta is from last_seed (which updates to current_seed)
            # packer.current_seed is updated by scan_for_best_transformation to 'seed'
            # But the 'seed' returned is absolute.
            # Delta = seed - last_seed.
            # Wait, `scan_for_best_transformation` searches relative to `self.current_seed`.
            # And it updates `self.current_seed` at the end.
            # So `seed` is the absolute new seed.
            # `last_seed` should be what `self.current_seed` WAS before update.
            # Actually, `scan_for_best_transformation` updates `self.current_seed`.
            # So `last_seed` is the previous seed.

            delta = seed - last_seed
            stream_buffer.extend(delta.to_bytes(4, 'big', signed=True))

            last_seed = seed

            # Residual
            stream_buffer.extend(residual_int.to_bytes(chunk_len_bytes, 'big'))

        # Compress the stream
        compressed_stream = zlib.compress(stream_buffer, level=9)

        with open(output_path, 'wb') as f:
            f.write(MAGIC_HEADER)
            f.write(original_len.to_bytes(8, 'big'))
            f.write(chunk_len_bits.to_bytes(4, 'big'))
            f.write(compressed_stream)

    def decompress_file(self, input_path, output_path):
        """
        Decompresses .nsp file.
        """
        with open(input_path, 'rb') as f:
            magic = f.read(4)
            if magic != MAGIC_HEADER:
                raise ValueError("Invalid File Format")

            original_len = int.from_bytes(f.read(8), 'big')
            chunk_len_bits = int.from_bytes(f.read(4), 'big')
            compressed_data = f.read()

        decompressed_stream = zlib.decompress(compressed_data)

        chunk_len_bytes = (chunk_len_bits + 7) // 8
        # Metadata is 5 bytes per chunk
        frame_size = 5 + chunk_len_bytes

        n_chunks = len(decompressed_stream) // frame_size

        output_buffer = bytearray()
        current_seed = 0

        # Instantiate PRNGs
        from src.prngs import PRNG_REGISTRY
        prngs = [cls() for cls in PRNG_REGISTRY]

        ptr = 0
        for i in range(n_chunks):
            # Parse Metadata
            flags = decompressed_stream[ptr]
            prng_id = flags & 0x03
            polarity = (flags >> 2) & 0x01

            delta_bytes = decompressed_stream[ptr+1 : ptr+5]
            delta = int.from_bytes(delta_bytes, 'big', signed=True)

            # Parse Residual
            residual_bytes = decompressed_stream[ptr+5 : ptr+5+chunk_len_bytes]
            residual_int = int.from_bytes(residual_bytes, 'big')

            ptr += frame_size

            # Reconstruct Seed
            seed = current_seed + delta
            current_seed = seed

            # Reconstruct Mask
            rng = prngs[prng_id]
            rng.seed(abs(seed)) # Seed must be positive for RNG, but delta logic handles abs?
            # In packer: `candidate = abs(self.current_seed + offset)`.
            # So logic handles abs.
            # But here `seed` can be negative if we just add delta?
            # Wait, `seed` tracks `current_seed`. `current_seed` in packer is always `best_candidate` which is abs().
            # Delta is `best_candidate - old_candidate`.
            # So `seed` should be positive.

            mask_bytes = rng.randbytes(chunk_len_bytes)
            mask_int = int.from_bytes(mask_bytes, 'big')

            # Restore Data
            # R = D ^ M (or ~D ^ M if polarity?)
            # Wait, packer logic:
            # Normal: xor_val = chunk ^ mask. Best_xor = xor_val. Polarity=0.
            # Inverted: xor_val = chunk ^ mask. Best_xor = xor_val ^ Ones. Polarity=1.

            # Restore:
            # If Polarity=0: D = R ^ M
            # If Polarity=1: R = (D^M)^Ones. => R^Ones = D^M => D = R^Ones^M.

            if polarity == 1:
                 all_ones = (1 << chunk_len_bits) - 1
                 # Invert residual first
                 residual_restore = residual_int ^ all_ones
                 data_int = residual_restore ^ mask_int
            else:
                 data_int = residual_int ^ mask_int

            output_buffer.extend(data_int.to_bytes(chunk_len_bytes, 'big'))

        # Truncate padding
        final_data = output_buffer[:original_len]

        with open(output_path, 'wb') as f:
            f.write(final_data)