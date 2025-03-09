from datetime import datetime, timedelta


class TokenBucketLimiter:
    def __init__(
        self,
        capacity: int,
        refill_rate: int,
        refill_interval: int,
    ):
        # 1. Initialize a bucket with a preset capacity
        self.token_num = capacity
        self.capacity = capacity
        # Tokens are put in the bucket at preset rates periodically
        self.refill_rate = refill_rate
        self.refill_interval = refill_interval
        self.last_updated = datetime.now()

    def acquire(self):
        # 2. Check for any pending refills; if there are, we'll refill the bucket.
        self._check_and_refill()

        # 3. When a request arrives, we check if there is at least one token left in the bucket.
        # If there is, we take one token out of the bucket, and the request goes through.
        if self.token_num > 0:
            self.token_num -= 1
            return True

        # 4. If there are no tokens in the bucket, the request is dropped and False is returned.
        return False

    def _check_and_refill(self):
        current = datetime.now()

        interval_num = int(
            (current - self.last_updated).total_seconds() // self.refill_interval
        )

        refill_count = interval_num * self.refill_rate

        self.token_num = min(self.token_num + refill_count, self.capacity)
        self.last_updated = min(
            current,
            self.last_updated + timedelta(seconds=refill_count * self.refill_interval),
        )
