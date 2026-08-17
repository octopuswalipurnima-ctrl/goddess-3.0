"""
AI Co-Host Engine for GODDESS AI 2.0.
Exports models, exceptions, managers, policies, intent detectors, and audit loggers.
"""

from app.services.cohost.audit import CoHostAuditLogger, cohost_audit_logger
from app.services.cohost.awareness import StreamAwarenessEngine, stream_awareness_engine
from app.services.cohost.context import CoHostContextManager, StreamContext, cohost_context_manager
from app.services.cohost.cooldowns import CoHostCooldownTracker, cohost_cooldown_tracker
from app.services.cohost.deduplication import ResponseDeduplicator, response_deduplicator
from app.services.cohost.engagement import EngagementDecisionEngine, engagement_decision_engine
from app.services.cohost.exceptions import (
    CoHostError,
    ContextLimitExceededError,
    InvalidCoHostConfigError,
    ResponseGenerationError,
    ResponsePolicyBlockedError,
)
from app.services.cohost.intents import RuleIntentDetector, rule_intent_detector
from app.services.cohost.knowledge import CreatorKnowledgeManager, creator_knowledge_manager
from app.services.cohost.manager import CoHostManager, cohost_manager
from app.services.cohost.models import (
    CoHostAuditRecord,
    CoHostConfig,
    CoHostIntent,
    CoHostMessage,
    CoHostMetrics,
    CoHostPersonality,
    CoHostResponse,
    CreatorKnowledge,
    EngagementDecision,
    EngagementResponseType,
    IntentType,
    ResponseStatus,
    StreamAwarenessData,
)
from app.services.cohost.personality import CoHostPersonalityManager, cohost_personality_manager
from app.services.cohost.response_generator import ResponseGenerator, response_generator
from app.services.cohost.response_policy import ResponsePolicy, response_policy

__all__ = [
    "CoHostError",
    "InvalidCoHostConfigError",
    "ResponseGenerationError",
    "ResponsePolicyBlockedError",
    "ContextLimitExceededError",
    "IntentType",
    "ResponseStatus",
    "EngagementResponseType",
    "EngagementDecision",
    "CreatorKnowledge",
    "StreamAwarenessData",
    "CoHostPersonality",
    "CoHostIntent",
    "CoHostMessage",
    "CoHostResponse",
    "CoHostConfig",
    "CoHostAuditRecord",
    "CoHostMetrics",
    "RuleIntentDetector",
    "rule_intent_detector",
    "StreamContext",
    "CoHostContextManager",
    "cohost_context_manager",
    "CoHostPersonalityManager",
    "cohost_personality_manager",
    "CreatorKnowledgeManager",
    "creator_knowledge_manager",
    "StreamAwarenessEngine",
    "stream_awareness_engine",
    "EngagementDecisionEngine",
    "engagement_decision_engine",
    "ResponseGenerator",
    "response_generator",
    "CoHostCooldownTracker",
    "cohost_cooldown_tracker",
    "ResponseDeduplicator",
    "response_deduplicator",
    "ResponsePolicy",
    "response_policy",
    "CoHostAuditLogger",
    "cohost_audit_logger",
    "CoHostManager",
    "cohost_manager",
]
