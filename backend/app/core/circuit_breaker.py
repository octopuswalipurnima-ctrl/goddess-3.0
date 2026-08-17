"""
Bounded Circuit Breakers for External Providers and Infrastructure in GODDESS AI 2.0.

Prevents retry storms, limits cascading failures, and manages automated
cooldown and half-open testing across YouTube, Gemini, Redis, and PostgreSQL.
"""

from enum import Enum
import time
from typing import Dict, Optional, Tuple
from app.core.logging import get_logger

logger = get_logger("core.circuit_breaker")


class CircuitBreakerState(str, Enum):
    CLOSED = "CLOSED"       # Normal operation: all requests allowed
    OPEN = "OPEN"           # Tripped: requests blocked immediately (fail-fast)
    HALF_OPEN = "HALF_OPEN" # Testing: limited trial requests to verify recovery


class CircuitBreaker:
    """Stateful circuit breaker with exponential cooldown and bounded trial requests."""

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout_seconds: float = 30.0,
        half_open_success_threshold: int = 2,
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout_seconds = recovery_timeout_seconds
        self.half_open_success_threshold = half_open_success_threshold

        self._state = CircuitBreakerState.CLOSED
        self._consecutive_failures = 0
        self._consecutive_successes = 0
        self._total_requests = 0
        self._total_failures = 0
        self._last_state_change = time.time()
        self._last_failure_time: Optional[float] = None
        self._cooldown_until: Optional[float] = None

    @property
    def state(self) -> CircuitBreakerState:
        """Evaluate state, transitioning from OPEN to HALF_OPEN if cooldown has elapsed."""
        now = time.time()
        if self._state == CircuitBreakerState.OPEN:
            if self._cooldown_until and now >= self._cooldown_until:
                self._transition_to(CircuitBreakerState.HALF_OPEN)
        return self._state

    def allow_request(self) -> Tuple[bool, str]:
        """
        Evaluate if a request should be permitted.
        Returns:
            (allowed: bool, reason: str)
        """
        current = self.state
        if current == CircuitBreakerState.CLOSED:
            return True, "Circuit closed (healthy)"
        elif current == CircuitBreakerState.HALF_OPEN:
            return True, "Circuit half-open (trial request)"
        else:
            remaining = max(0.0, (self._cooldown_until or 0.0) - time.time())
            return False, f"Circuit OPEN for '{self.name}'. Cooldown active for {remaining:.1f}s"

    def record_success(self) -> None:
        """Record a successful operation."""
        self._total_requests += 1
        self._consecutive_failures = 0

        if self._state == CircuitBreakerState.HALF_OPEN:
            self._consecutive_successes += 1
            if self._consecutive_successes >= self.half_open_success_threshold:
                self._transition_to(CircuitBreakerState.CLOSED)

    def record_failure(self, error: Optional[str] = None) -> None:
        """Record a failed operation, tripping the breaker if threshold is exceeded."""
        self._total_requests += 1
        self._total_failures += 1
        self._consecutive_failures += 1
        self._consecutive_successes = 0
        self._last_failure_time = time.time()

        if self._state == CircuitBreakerState.HALF_OPEN:
            # Any failure in HALF_OPEN immediately trips back to OPEN
            self._transition_to(CircuitBreakerState.OPEN)
        elif self._state == CircuitBreakerState.CLOSED:
            if self._consecutive_failures >= self.failure_threshold:
                self._transition_to(CircuitBreakerState.OPEN)

    def _transition_to(self, new_state: CircuitBreakerState) -> None:
        old_state = self._state
        self._state = new_state
        self._last_state_change = time.time()

        if new_state == CircuitBreakerState.OPEN:
            # Calculate cooldown (with backoff up to 300s)
            cooldown = min(self.recovery_timeout_seconds * (2 ** max(0, self._consecutive_failures - self.failure_threshold)), 300.0)
            self._cooldown_until = time.time() + cooldown
            logger.warning(f"CircuitBreaker '{self.name}' TRIPPED to OPEN ({cooldown:.1f}s cooldown).")
        elif new_state == CircuitBreakerState.HALF_OPEN:
            self._consecutive_successes = 0
            logger.info(f"CircuitBreaker '{self.name}' transitioned to HALF_OPEN (trialing recovery).")
        elif new_state == CircuitBreakerState.CLOSED:
            self._consecutive_failures = 0
            self._consecutive_successes = 0
            self._cooldown_until = None
            logger.info(f"CircuitBreaker '{self.name}' RESET to CLOSED (healthy).")

    def get_diagnostics(self) -> Dict[str, any]:
        """Safe diagnostics without sensitive data."""
        return {
            "name": self.name,
            "state": self.state.value,
            "consecutive_failures": self._consecutive_failures,
            "consecutive_successes": self._consecutive_successes,
            "total_requests": self._total_requests,
            "total_failures": self._total_failures,
            "cooldown_remaining_seconds": max(0.0, (self._cooldown_until or 0.0) - time.time()) if self._cooldown_until else 0.0,
        }

    def reset(self) -> None:
        """Explicitly reset breaker to CLOSED."""
        self._transition_to(CircuitBreakerState.CLOSED)


class CircuitBreakerRegistry:
    """Central registry of circuit breakers for infrastructure and providers."""

    def __init__(self):
        self._breakers: Dict[str, CircuitBreaker] = {
            "youtube": CircuitBreaker("youtube", failure_threshold=5, recovery_timeout_seconds=30.0),
            "gemini": CircuitBreaker("gemini", failure_threshold=5, recovery_timeout_seconds=20.0),
            "redis": CircuitBreaker("redis", failure_threshold=3, recovery_timeout_seconds=15.0),
            "postgres": CircuitBreaker("postgres", failure_threshold=3, recovery_timeout_seconds=15.0),
        }

    def get(self, name: str) -> CircuitBreaker:
        if name not in self._breakers:
            self._breakers[name] = CircuitBreaker(name)
        return self._breakers[name]

    def get_all_diagnostics(self) -> Dict[str, Dict[str, any]]:
        return {k: v.get_diagnostics() for k, v in self._breakers.items()}


# Global singleton
circuit_breakers = CircuitBreakerRegistry()
