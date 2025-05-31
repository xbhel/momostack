from datetime import datetime, timedelta


class TokenBucketLimiter:
    def __init__(
        self,
        capacity: int,
        refill_rate: int,
        refill_interval: int,
    ):
        """
        Initialize a bucket with a preset capacity
        :param capacity: Maximum number of tokens the bucket can hold.
        :param refill_rate: Number of tokens added per refill interval.
        :param refill_interval: Time interval (in seconds) at which tokens are added.
        """
        
        # 1. Initialize a bucket with a preset capacity
        self.token_num = capacity
        self.capacity = capacity
        # Tokens are put in the bucket at preset rates periodically
        self.refill_rate = refill_rate
        self.refill_interval = refill_interval
        self.last_updated = datetime.now()

    def acquire(self):
        # 2. Check for any pending refills; if there are, we'll refill the bucket.
        self._refill()

        # 3. If tokens are available, consume one and allow the request
        if self.token_num > 0:
            self.token_num -= 1
            return True

        # 4. If no tokens are available, the request is denied
        return False

    def _refill(self):
        """
        Replenishes tokens in the bucket based on the elapsed time since the last update.
        """
        current_time = datetime.now()
        elapsed_intervals = (current_time - self.last_updated).total_seconds() // self.refill_interval

        if elapsed_intervals > 0:
            # Calculate how many tokens should be added
            refill_count = int(elapsed_intervals * self.refill_rate)
            self.token_num = min(self.token_num + refill_count, self.capacity)
            # Update the last updated timestamp accordingly
            self.last_updated = min(
                current_time,
                self.last_updated + timedelta(seconds=refill_count * self.refill_interval),
            )
