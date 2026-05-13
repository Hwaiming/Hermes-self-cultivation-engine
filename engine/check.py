#!/usr/bin/env python3
"""
Self-Cultivation Engine · Self-Check CLI

Runs all detectors, produces evidence with SHA-256 hashes,
and prints a summary report.

Usage:
  python3 -m engine.check                     # Run all checks
  python3 -m engine.check --detector over_fusion  # Single detector
  python3 -m engine.check --json              # JSON output
  python3 -m engine.check --evidence          # Show evidence store
"""

import os
import sys
import json
import argparse
from pathlib import Path

# Add parent to path for standalone execution
_ENGINE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_ENGINE_DIR))

from detectors.registry import get_registry, DetectorRegistry
from detectors.base import Severity
from evidence.store import EvidenceStore, EvidenceRecord


def main():
    parser = argparse.ArgumentParser(description="Self-Cultivation Engine · Self-Check")
    parser.add_argument("--detector", "-d", type=str, help="Run a specific detector only")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--evidence", action="store_true", help="Show evidence store summary")
    parser.add_argument("--context", type=str, help="JSON file with context data")
    args = parser.parse_args()
    
    evidence_store = EvidenceStore()
    
    if args.evidence:
        summary = evidence_store.summary()
        if args.json:
            print(json.dumps(summary, ensure_ascii=False, indent=2))
        else:
            print(f"\n{'='*60}")
            print(f"  Evidence Store Summary")
            print(f"{'='*60}")
            print(f"  Total records: {summary['total']}")
            print(f"  Passed:   {summary['passed']}")
            print(f"  Failed:   {summary['failed']}")
            print(f"  Verified: {summary['verified']}")
            if summary['tampered'] > 0:
                print(f"  ⚠️  TAMPERED: {summary['tampered']}")
            
            records = evidence_store.list_recent(limit=5)
            if records:
                print(f"\n  Recent records:")
                for r in records:
                    status = "✅" if r.get("passed") else "❌"
                    verified = "🔒" if r.get("_verified") else "⚠️"
                    print(f"    {status}{verified} {r.get('check_type','?')}")
            print(f"{'='*60}\n")
        return 0
    
    # Load context
    context = {}
    if args.context:
        try:
            with open(args.context, "r") as f:
                context = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error loading context: {e}")
            return 1
    
    # Run detectors
    registry = get_registry()
    
    if args.detector:
        results = [registry.run_detector(args.detector, context)]
    else:
        results = registry.run_all(context)
    
    # Save evidence
    for r in results:
        record = EvidenceRecord(
            check_type=f"detector.{r.detector_name}",
            result=r.message,
            passed=r.passed,
            detail=json.dumps(r.to_dict(), ensure_ascii=False),
        )
        path = evidence_store.save(record)
        r._evidence_path = path
    
    if args.json:
        output = []
        for r in results:
            d = r.to_dict()
            d["sha256"] = r.sha256
            d["evidence_file"] = getattr(r, "_evidence_path", "")
            output.append(d)
        print(json.dumps(output, ensure_ascii=False, indent=2))
        return 0
    
    # Text report
    summary = registry.summary(results)
    
    print(f"\n{'='*60}")
    print(f"  Self-Check Report")
    print(f"{'='*60}")
    print(f"  Detectors: {summary['total']} | ✅ {summary['passed']} | ❌ {summary['failed']}")
    
    for sev in ("deny", "block", "warn"):
        if sev in summary["by_severity"]:
            s = summary["by_severity"][sev]
            icon = {"deny": "🔴", "block": "🟡", "warn": "🟢"}.get(sev, "○")
            print(f"  {icon} {sev}: {s['failed']}/{s['total']} failed")
            if s["detectors"]:
                for d in s["detectors"]:
                    print(f"       → {d}")
    
    print()
    for r in results:
        icon = "✅" if r.passed else "❌"
        print(f"  {icon} [{r.severity.value:5s}] {r.detector_name}")
        if not r.passed:
            print(f"       {r.message}")
        print(f"       sha256: {r.sha256[:16]}...")
        ep = getattr(r, "_evidence_path", "")
        if ep:
            print(f"       {ep}")
    
    print(f"{'='*60}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
