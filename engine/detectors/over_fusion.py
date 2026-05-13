"""
Detector: Over-Fusion — When similar concepts get auto-merged.

Trigger: Multiple related concepts referenced simultaneously under time pressure.
Behavior: Distinctions between concepts are unconsciously smoothed over.
"""

from .base import BaseDetector, Severity, CheckResult, EvidenceItem


class OverFusionDetector(BaseDetector):
    name = "over_fusion"
    description = "Detects when similar concepts are merged without checking distinctions"
    severity = Severity.WARN
    
    def check(self, context: dict = None) -> CheckResult:
        ctx = context or {}
        
        # How many distinct sources being referenced?
        sources = ctx.get("sources", [])
        if len(sources) >= 2:
            # Check if distinct sources are being treated as one
            source_names = set()
            for s in sources:
                for token in s.get("name", "").lower().split():
                    source_names.add(token)
            
            # If multiple sources share keywords but are distinct, potential fusion
            shared = len(sources) - len(source_names) if source_names else 0
            if shared > 0:
                return self.failed(
                    f"Multiple sources share overlapping keywords ({shared} overlaps)",
                    evidence=[
                        EvidenceItem(
                            kind="pattern_match",
                            description=f"Sources: {[s.get('name','') for s in sources]}",
                            value=float(shared),
                        )
                    ],
                )
        
        # Check if similar concepts are treated as identical
        concepts = ctx.get("concepts", [])
        if len(concepts) >= 2:
            for i, c1 in enumerate(concepts):
                for c2 in concepts[i+1:]:
                    if c1.get("name") and c2.get("name"):
                        # Similar names but should be distinct
                        n1, n2 = c1["name"].lower(), c2["name"].lower()
                        if (n1 in n2 or n2 in n1) and c1.get("distinct_from", []) and n2 not in [x.lower() for x in c1["distinct_from"]]:
                            return self.failed(
                                f"'{c1['name']}' and '{c2['name']}' may be fused",
                                evidence=[
                                    EvidenceItem(
                                        kind="pattern_match",
                                        description=f"'{c1['name']}' (distinct_from: {c1.get('distinct_from',[])}) vs '{c2['name']}'",
                                    )
                                ],
                            )
        
        return self.passed()
