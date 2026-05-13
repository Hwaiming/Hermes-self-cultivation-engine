"""
Detector: Post-Correction Defensiveness — "but...however..." after being corrected.

Trigger: Immediately after receiving a correction from the user.
Behavior: First response includes "but", "however", "my point was", softening language.
"""

import re

from .base import BaseDetector, Severity, CheckResult, EvidenceItem


class PostCorrectionDefenseDetector(BaseDetector):
    name = "post_correction_defense"
    description = "Detects defensive language after being corrected"
    severity = Severity.BLOCK
    
    DEFENSIVE_PATTERNS = [
        r'\bbut\b',
        r'\bhowever\b',
        r'\bthat\'?s? what I meant\b',
        r'\bmy point (?:was|is)\b',
        r'\bwhat I was (?:trying to )?say(?:ing)?\b',
        r'\bI was (?:just |only )?\b',
        r'\btechnically\b',
        r'\bto be fair\b',
        r'\bin my defense\b',
        r'\byou (?:misunderstood|misinterpreted|missed|misheard)\b',
        r'\bI already (?:said|mentioned|noted)\b',
    ]
    
    def check(self, context: dict = None) -> CheckResult:
        ctx = context or {}
        output = ctx.get("output", "")
        was_corrected = ctx.get("was_corrected", False)
        
        if not was_corrected or not output:
            return self.passed()
        
        # Check first 200 chars for defensive patterns
        first_part = output[:200]
        
        matches = []
        for pattern in self.DEFENSIVE_PATTERNS:
            if re.search(pattern, first_part, re.IGNORECASE):
                matches.append(pattern)
        
        if matches:
            return self.failed(
                f"Defensive language detected in correction response ({len(matches)} patterns)",
                evidence=[
                    EvidenceItem(
                        kind="regex_match",
                        description=f"Matching patterns: {matches}",
                        value=float(len(matches)),
                        threshold=1.0,
                    )
                ],
            )
        
        # Check if "Noted. Thank you." or similar is absent
        acceptance_patterns = [
            r'\bnoted\b',
            r'\bthank you\b',
            r'\b受教\b',
            r'\b你说得对\b',
            r'\byou\'?r?e? right\b',
        ]
        
        has_acceptance = any(re.search(p, output[:100], re.IGNORECASE) for p in acceptance_patterns)
        if not has_acceptance:
            return self.failed(
                "No acceptance signal found in correction response",
                evidence=[
                    EvidenceItem(
                        kind="pattern_match",
                        description="Expected 'Noted' or similar acceptance phrase in first 100 chars",
                    )
                ],
            )
        
        return self.passed()
