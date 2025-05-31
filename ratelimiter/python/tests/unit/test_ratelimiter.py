import unittest
from time import sleep

import __import_side_effect  # noqa: F401
from ratelimiter import TokenBucketLimiter


class TestTokenBucketLimiter(unittest.TestCase):
    def test_acquire(self):
        # Create a token bucket with a capacity of 4 tokens.
        # Tokens are refilled at a rate of 2 tokens per second.
        token_bucket_limiter = TokenBucketLimiter(4, 2, 1)

        # The bucket starts full (4 tokens), so the first four requests should succeed.
        self.assertTrue(token_bucket_limiter.acquire())
        self.assertTrue(token_bucket_limiter.acquire())
        self.assertTrue(token_bucket_limiter.acquire())
        self.assertTrue(token_bucket_limiter.acquire())

        # The bucket is now empty; additional requests should be denied.
        self.assertFalse(token_bucket_limiter.acquire())

    def test_acquire_with_wait(self):
        token_bucket_limiter = TokenBucketLimiter(4, 2, 1)

        # Consume all available tokens.
        self.assertTrue(token_bucket_limiter.acquire())
        self.assertTrue(token_bucket_limiter.acquire())
        self.assertTrue(token_bucket_limiter.acquire())
        self.assertTrue(token_bucket_limiter.acquire())

        # Wait for 1 second to allow 2 tokens to be refilled.
        sleep(1)

        # Two more requests should now succeed.
        self.assertTrue(token_bucket_limiter.acquire())
        self.assertTrue(token_bucket_limiter.acquire())

        # The bucket is empty again; further requests should be denied.
        self.assertFalse(token_bucket_limiter.acquire())


if __name__ == "__main__":
    unittest.main()
