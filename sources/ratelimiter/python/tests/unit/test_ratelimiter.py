import unittest
from time import sleep

import __import_side_effect  # noqa: F401
from ratelimiter import TokenBucketLimiter


class TestTokenBucketLimiter(unittest.TestCase):
    def test_acquire(self):
        # Initialize a token bucket with a maximum capacity of 4 tokens.
        # Tokens are added to the bucket at a fixed rate of 2 tokens per second.
        token_bucket_limiter = TokenBucketLimiter(4, 2, 1)

        # Initially, the bucket is full (contains 4 tokens), so the first four requests succeed.
        self.assertTrue(token_bucket_limiter.acquire())
        self.assertTrue(token_bucket_limiter.acquire())
        self.assertTrue(token_bucket_limiter.acquire())
        self.assertTrue(token_bucket_limiter.acquire())

        # capacity exhausted
        # The bucket is now empty; additional requests will be denied.
        self.assertFalse(token_bucket_limiter.acquire())

    def test_acquire_with_wait(self):
        token_bucket_limiter = TokenBucketLimiter(4, 2, 1)

        self.assertTrue(token_bucket_limiter.acquire())
        self.assertTrue(token_bucket_limiter.acquire())
        self.assertTrue(token_bucket_limiter.acquire())
        self.assertTrue(token_bucket_limiter.acquire())

        # 2 tokens will be refilled to the bucket
        sleep(1)

        self.assertTrue(token_bucket_limiter.acquire())
        self.assertTrue(token_bucket_limiter.acquire())

        # capacity exhausted
        self.assertFalse(token_bucket_limiter.acquire())


if __name__ == "__main__":
    unittest.main()
