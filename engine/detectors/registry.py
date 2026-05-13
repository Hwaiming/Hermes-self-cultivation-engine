"""
Self-Cultivation Engine · Detector Registry

Loads all detectors from the detectors/ directory,
runs them against a given context, and aggregates results.
"""

import os
import importlib
import pkgutil
from typing import Optional
from pathlib import Path

from .base import BaseDetector, CheckResult, Severity


class DetectorRegistry:
    """
    Registry of all available detectors.
    
    Usage:
        registry = DetectorRegistry()
        results = registry.run_all(context={...})
        
        for r in results:
            if not r.passed:
                print(f"[{r.severity.value}] {r.detector}: {r.message}")
                print(f"  evidence: {r.sha256}")
    """
    
    def __init__(self):
        self._detectors: dict[str, BaseDetector] = {}
        self._load_detectors()
    
    def _load_detectors(self):
        """Auto-discover all detector modules in the detectors package."""
        pkg_dir = Path(__file__).parent
        
        for importer, modname, ispkg in pkgutil.iter_modules([str(pkg_dir)]):
            if modname in ("base", "__init__"):
                continue
            
            try:
                module = importlib.import_module(f".{modname}", __package__)
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if isinstance(attr, type) and issubclass(attr, BaseDetector) and attr_name != "BaseDetector":
                        instance = attr()
                        self._detectors[instance.name] = instance
            except Exception as e:
                print(f"  ⚠️  Failed to load detector '{modname}': {e}")
    
    @property
    def detectors(self) -> dict[str, BaseDetector]:
        return dict(self._detectors)
    
    def run_all(self, context: Optional[dict] = None) -> list[CheckResult]:
        """Run all registered detectors and return results."""
        results = []
        for name, detector in sorted(self._detectors.items()):
            try:
                result = detector.check(context)
                results.append(result)
            except Exception as e:
                results.append(CheckResult(
                    detector_name=name,
                    severity=Severity.WARN,
                    passed=False,
                    message=f"Detector error: {e}",
                ))
        return results
    
    def run_detector(self, name: str, context: Optional[dict] = None) -> CheckResult:
        """Run a specific detector by name."""
        detector = self._detectors.get(name)
        if not detector:
            return CheckResult(
                detector_name=name,
                severity=Severity.WARN,
                passed=False,
                message=f"Detector '{name}' not found",
            )
        return detector.check(context)
    
    def summary(self, results: list[CheckResult]) -> dict:
        """Aggregate results into a summary dict."""
        passed = sum(1 for r in results if r.passed)
        failed = sum(1 for r in results if not r.passed)
        by_severity = {}
        for r in results:
            sev = r.severity.value
            by_severity.setdefault(sev, {"total": 0, "failed": 0, "detectors": []})
            by_severity[sev]["total"] += 1
            if not r.passed:
                by_severity[sev]["failed"] += 1
                by_severity[sev]["detectors"].append(r.detector_name)
        
        return {
            "total": len(results),
            "passed": passed,
            "failed": failed,
            "by_severity": by_severity,
        }


# Singleton
_registry: Optional[DetectorRegistry] = None


def get_registry() -> DetectorRegistry:
    global _registry
    if _registry is None:
        _registry = DetectorRegistry()
    return _registry


def run_detectors(context: Optional[dict] = None) -> list[CheckResult]:
    """Convenience: get registry and run all detectors."""
    return get_registry().run_all(context)
