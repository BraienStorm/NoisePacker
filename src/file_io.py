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
        [CHUNK_SIZE_BITS:4]
        [ZLIB_PAYLOAD: Variable]
            Sequence of:
            [METADATA] + [TRANSFORMED_RESIDUAL]

            Metadata Logic:
            - Byte 0 (Flags):
              - Bit 7 (0x80): JUMP_FLAG (1=Switch Dim, 0=Stay)
              - Bit 6 (0x40): POLARITY (1=Invert, 0=Normal)
              - If JUMP_FLAG=1: Bits 0-1 (0x03) = NEW_ID
              - If JUMP_FLAG=0: Bits 0-5 Unused.
            - Bytes 1-4: SEED_DELTA (Signed 32-bit)
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

        stream_buffer = bytearray()

        self.packer.current_seed = 0
        last_seed = 0
        last_prng_id = 0 # Default starting dimension is 0

        for i in range(n_chunks):
            chunk_bytes = padded_data[i*chunk_len_bytes : (i+1)*chunk_len_bytes]
            chunk_int = int.from_bytes(chunk_bytes, 'big')

            # Find best transformation
            seed, prng_id, residual_int, ratio, polarity = self.packer.scan_for_best_transformation(chunk_int, chunk_len_bits)

            # Metadata Construction
            flags = 0

            # Polarity Flag (Bit 6)
            if polarity == 1:
                flags |= 0x40

            # Jump Flag logic
            if prng_id != last_prng_id:
                flags |= 0x80 # Set JUMP_FLAG
                flags |= (prng_id & 0x03) # Store new ID in low bits
                last_prng_id = prng_id
            else:
                # JUMP_FLAG is 0. ID bits ignored.
                pass

            stream_buffer.append(flags)

            # Seed Delta
            delta = int(seed - last_seed)
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
        frame_size = 5 + chunk_len_bytes

        n_chunks = len(decompressed_stream) // frame_size

        output_buffer = bytearray()
        current_seed = 0
        current_prng_id = 0

        # Instantiate PRNGs
        from src.prngs import PRNG_REGISTRY
        import copy
        prngs = copy.deepcopy(PRNG_REGISTRY)

        ptr = 0
        for i in range(n_chunks):
            # Parse Metadata
            flags = decompressed_stream[ptr]

            jump_flag = (flags >> 7) & 0x01
            polarity = (flags >> 6) & 0x01

            if jump_flag == 1:
                current_prng_id = flags & 0x03
            else:
                # Keep existing current_prng_id
                pass

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
            rng = prngs[current_prng_id]
            rng.seed(abs(seed))

            mask_bytes = rng.randbytes(chunk_len_bytes)
            mask_int = int.from_bytes(mask_bytes, 'big')

            # Restore Data
            if polarity == 1:
                 all_ones = (1 << chunk_len_bits) - 1
                 residual_restore = residual_int ^ all_ones
                 data_int = residual_restore ^ mask_int
            else:
                 data_int = residual_int ^ mask_int

            output_buffer.extend(data_int.to_bytes(chunk_len_bytes, 'big'))

        # Truncate padding
        final_data = output_buffer[:original_len]

        with open(output_path, 'wb') as f:
            f.write(final_data)