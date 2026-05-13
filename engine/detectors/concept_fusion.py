"""
Detector: Concept Fusion Without Source Check — Merging concepts without verifying.

Trigger: High information volume and time pressure.
Behavior: Similar concepts from different sources automatically fused.
"""

from .base import BaseDetector, Severity, CheckResult, EvidenceItem


class ConceptFusionDetector(BaseDetector):
    name = "concept_fusion"
    description = "Detects when concepts from different sources are fused without source verification"
    severity = Severity.WARN
    
    def check(self, context: dict = None) -> CheckResult:
        ctx = context or {}
        sources = ctx.get("sources_cited", [])
        
        if len(sources) < 2:
            return self.passed()
        
        # Track source-concept pairs
        source_concept_map = {}
        for s in sources:
            src_name = s.get("name", "")
            concepts = s.get("concepts", [])
            for c in concepts:
                cname = c.get("name", "").lower()
                if cname not in source_concept_map:
                    source_concept_map[cname] = set()
                source_concept_map[cname].add(src_name)
        
        # A concept claimed by multiple sources should have source checks
        fused = {c: ss for c, ss in source_concept_map.items() if len(ss) >= 2}
        
        if fused:
            return self.failed(
                f"{len(fused)} concept(s) attributed to multiple sources without verification",
                evidence=[
                    EvidenceItem(
                        kind="pattern_match",
                        description=f"Concepts: {dict((k, list(v)) for k, v in fused.items())}",
                        value=float(len(fused)),
                    )
                ],
            )
        
        # Check if source distinctions are noted
        has_distinctions = ctx.get("source_distinctions_noted", False)
        if not has_distinctions:
            return self.failed(
                "No source distinctions noted despite multiple sources",
                evidence=[
                    EvidenceItem(
                        kind="pattern_match",
                        description=f"{len(sources)} sources used but no distinctions between them",
                        value=float(len(sources)),
                    )
                ],
            )
        
        return self.passed()
