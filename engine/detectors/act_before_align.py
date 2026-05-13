"""
Detector: Act Before Align — Found a problem and acted without aligning first.

Trigger: Discovering a problem or improvement opportunity.
Behavior: Default reaction is "let me fix it" without checking existing solutions.
"""

from .base import BaseDetector, Severity, CheckResult, EvidenceItem


class ActBeforeAlignDetector(BaseDetector):
    name = "act_before_align"
    description = "Detects when the agent fixes before asking"
    severity = Severity.BLOCK
    
    FIX_PHRASES = [
        "let me fix",
        "let me correct",
        "I'll fix",
        "I'll correct",
        "I'll update",
        "let me update",
        "I'll change",
        "let me change",
        "I'll modify",
        "I'll rebuild",
        "我来修",
        "我来改",
        "我来修复",
        "我直接改",
    ]
    
    ALIGN_PHRASES = [
        "let me check",
        "let me look",
        "let me verify",
        "should I",
        "shall I",
        "do you want",
        "let me ask",
        "let me confirm",
        "which approach",
        "先确认",
        "要不要",
        "我先查",
        "我先确认",
    ]
    
    def check(self, context: dict = None) -> CheckResult:
        ctx = context or {}
        output = ctx.get("output", "")
        has_multiple_options = ctx.get("has_multiple_options", False)
        found_problem = ctx.get("found_problem", False)
        
        if not output or not found_problem:
            return self.passed()
        
        output_lower = output.lower()
        
        # Count fix vs align phrases in first 300 chars
        fix_count = sum(1 for p in self.FIX_PHRASES if p in output_lower)
        align_count = sum(1 for p in self.ALIGN_PHRASES if p in output_lower)
        
        # If found a problem AND has multiple options AND fix > align
        if has_multiple_options and fix_count > 0 and fix_count > align_count:
            return self.failed(
                f"Fixed before aligning (fix phrases: {fix_count}, align phrases: {align_count})",
                evidence=[
                    EvidenceItem(
                        kind="pattern_match",
                        description=f"Problem found with {ctx.get('option_count', 0)} options available",
                        value=float(fix_count - align_count),
                        threshold=1.0,
                    )
                ],
            )
        
        # Even without multiple options, "I'll fix" without any alignment check
        if fix_count > 0 and align_count == 0:
            return self.failed(
                f"Direct fix without any alignment check ({fix_count} fix phrases)",
                evidence=[
                    EvidenceItem(
                        kind="pattern_match",
                        description="No alignment phrases found in first 300 chars",
                        value=float(fix_count),
                    )
                ],
            )
        
        return self.passed()
