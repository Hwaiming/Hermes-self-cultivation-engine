"""
Detector: Guess When Uncertain — Pretending certainty when information is incomplete.

Trigger: Answering a question without sufficient data.
Behavior: Uses "maybe", "probably", "I think" to hedge uncertainty.
"""

import re

from .base import BaseDetector, Severity, CheckResult, EvidenceItem


class GuessWhenUncertainDetector(BaseDetector):
    name = "guess_when_uncertain"
    description = "Detects when the agent hedges uncertainty with vague language"
    severity = Severity.WARN
    
    # Patterns that indicate hedging rather than genuine uncertainty
    HEDGE_PATTERNS = [
        r'\b(maybe|perhaps|possibly|probably)\b',
        r'\bI think\b',
        r'\bI believe\b',
        r'\bI guess\b',
        r'\bI assume\b',
        r'\bmost likely\b',
        r'\b(?:it|could)\s+(?:might|may|could)\s+be\b',
        r'\bnot sure but\b',
    ]
    
    def check(self, context: dict = None) -> CheckResult:
        ctx = context or {}
        output = ctx.get("output", "")
        
        if not output:
            return self.passed()
        
        matches = []
        for pattern in self.HEDGE_PATTERNS:
            for m in re.finditer(pattern, output, re.IGNORECASE):
                matches.append(m.group())
        
        if len(matches) >= 3:
            return self.failed(
                f"Output contains {len(matches)} hedge phrases suggesting uncertainty",
                evidence=[
                    EvidenceItem(
                        kind="regex_match",
                        description=f"Hedge phrases: {matches[:5]}",
                        value=float(len(matches)),
                        threshold=3.0,
                    )
                ],
            )
        
        # Check if output sounds confident but context shows uncertainty
        ctx_uncertainty = ctx.get("uncertainty_flags", [])
        if ctx_uncertainty and len(matches) == 0:
            # Output is confident despite known uncertainty — potentially worse
            return self.failed(
                f"Output is confident despite {len(ctx_uncertainty)} uncertainty flags",
                evidence=[
                    EvidenceItem(
                        kind="pattern_match",
                        description=f"Context flags: {ctx_uncertainty}",
                        value=float(len(ctx_uncertainty)),
                    )
                ],
            )
        
        return self.passed()
