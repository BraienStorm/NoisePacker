import unittest
import os
import hashlib
from src.file_io import NoisePackerFile

class TestFileIO(unittest.TestCase):
    def test_round_trip(self):
        """Test compressing and decompressing a random file."""
        input_file = "test_input.bin"
        compressed_file = "test_output.nsp"
        restored_file = "test_restored.bin"

        # 1. Create Random Input (10 KB)
        data = os.urandom(10 * 1024)
        with open(input_file, 'wb') as f:
            f.write(data)

        original_hash = hashlib.md5(data).hexdigest()

        # 2. Compress
        packer = NoisePackerFile()
        packer.compress_file(input_file, compressed_file)

        # 3. Decompress
        packer.decompress_file(compressed_file, restored_file)

        # 4. Verify
        with open(restored_file, 'rb') as f:
            restored_data = f.read()

        restored_hash = hashlib.md5(restored_data).hexdigest()

        self.assertEqual(len(data), len(restored_data), "Length mismatch")
        self.assertEqual(original_hash, restored_hash, "Hash mismatch - Data corruption!")

        # Cleanup
        os.remove(input_file)
        os.remove(compressed_file)
        os.remove(restored_file)

if __name__ == '__main__':
    unittest.main()