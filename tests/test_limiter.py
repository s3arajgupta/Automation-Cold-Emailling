from coldmail.limiter import RateLimiter


def test_rate_limiter_domain_throttle():
    limiter = RateLimiter(min_delay=0.01, max_delay=0.02, max_per_domain=2)

    allowed, _ = limiter.can_send_to_domain("example.com")
    assert allowed is True
    limiter.record_sent("example.com")

    allowed, _ = limiter.can_send_to_domain("example.com")
    assert allowed is True
    limiter.record_sent("example.com")

    # 3rd send to same domain should be throttled
    allowed, reason = limiter.can_send_to_domain("example.com")
    assert allowed is False
    assert "Domain limit reached" in reason

    # Different domain should still be allowed
    allowed, _ = limiter.can_send_to_domain("otherdomain.org")
    assert allowed is True


def test_rate_limiter_jitter_dry_run():
    limiter = RateLimiter(min_delay=5.0, max_delay=10.0)
    delay = limiter.wait_jitter(dry_run=True)
    assert 5.0 <= delay <= 10.0
