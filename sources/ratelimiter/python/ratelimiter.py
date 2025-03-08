from datetime import datetime


class TokenBucketLimiter:
    def __init__(
        self,
        capacity: int,
        refill_rate: int,
        refill_interval: int,
    ):
        # 1. Initialize a bucket with capacity
        self.token_num = capacity
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.refill_interval = refill_interval
        self.last_updated = datetime.now()

    def acquire(self):
        # 2. Check for any pending refills; if there are, we'll refill the bucket.
        self._check_and_refill()

        # 3. When a request is made, a token is removed from the bucket.
        if self.token_num > 0:
            self.token_num -= 1
            return True

        # 4. If there are no tokens in the bucket, False is returned.
        return False

    def _check_and_refill(self):
        current = datetime.now()

        interval_num = (
            current - self.last_updated
        ).total_seconds() / self.refill_interval

        refill_count = min(interval_num * self.refill_rate, self.capacity)

        if refill_count > 0:
            self.token_num += refill_count
