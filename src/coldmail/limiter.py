"""Smart deliverability rate limiter with jittered backoff and domain throttling."""

from __future__ import annotations

import random
import time
from collections import defaultdict
from typing import Tuple


class RateLimiter:
    """Controls dispatch cadence to protect sender domain reputation."""

    def __init__(
        self,
        min_delay: float = 8.0,
        max_delay: float = 18.0,
        max_per_domain: int = 5,
    ) -> None:
        self.min_delay = max(0.0, min_delay)
        self.max_delay = max(self.min_delay, max_delay)
        self.max_per_domain = max_per_domain
        self.domain_counts: dict[str, int] = defaultdict(int)

    def can_send_to_domain(self, domain: str) -> Tuple[bool, str]:
        """Check if sending to this domain exceeds the safe domain velocity limit."""
        if not domain:
            return True, ""

        count = self.domain_counts[domain]
        if self.max_per_domain > 0 and count >= self.max_per_domain:
            return (
                False,
                f"Domain limit reached ({count}/{self.max_per_domain} emails to @{domain} in this session)",
            )
        return True, ""

    def record_sent(self, domain: str) -> None:
        """Increment count of sent emails for domain."""
        if domain:
            self.domain_counts[domain] += 1

    def wait_jitter(self, dry_run: bool = False) -> float:
        """Wait a randomized jitter delay between sends. Returns seconds waited."""
        if self.max_delay <= 0 or self.min_delay <= 0:
            return 0.0

        delay = round(random.uniform(self.min_delay, self.max_delay), 2)
        if not dry_run:
            time.sleep(delay)
        return delay
