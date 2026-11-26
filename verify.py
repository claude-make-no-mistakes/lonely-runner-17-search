"""Independent rational replay of selected branches and census coverage."""

import argparse
from collections import Counter
from fractions import Fraction
from itertools import combinations
import json
from math import floor
from pathlib import Path


Q = 17
THRESHOLD = Fraction(1, Q)
DENSITY = 2 * THRESHOLD
BASE = tuple(range(1, Q))


def check(condition, message):
    if not condition:
        raise ValueError(message)


def window(region, speed):
    # Enumerate unit lobes in wt coordinates, then clip by interval overlap.
    pieces = []
    for a, b in region:
        for k in range(floor(a*speed), floor(b*speed)+1):
            left = (k+THRESHOLD)/speed
            right = (k+1-THRESHOLD)/speed
            if left <= b and right >= a:
                pieces.append((max(a, left), min(b, right)))
    return pieces


def all_windows(speeds):
    region = [(Fraction(0), Fraction(1, 2))]
    for speed in speeds:
        region = window(region, speed)
    return region


def replay(removed):
    counts = Counter()
    limits = Counter()
    tight = []

    def extend(region, remaining, low, chosen):
        width = max((b-a for a, b in region), default=Fraction())
        if remaining == 0:
            check(region, "Found counterexample while replaying")
            if width == 0:
                tight.append({"inserted": list(chosen), "times": [str(a) for a, _ in region]})
                counts["tight"] += 1
            return
        check(width > 0, "Found a degenerate prefix during replay")
        bound = (DENSITY if remaining == 1 else
                 remaining*DENSITY*(1-DENSITY)/(1-remaining*DENSITY)) / width
        maximum = floor(bound)
        counts[f"nodes_{remaining}"] += 1
        limits[str(remaining)] = max(limits[str(remaining)], maximum)
        for speed in range(low, maximum+1):
            counts[f"tried_{remaining}"] += 1
            # At the last speed, compute the entire intersection directly.
            # This avoids the search's bad-arc containment prefilter.
            extend(window(region, speed), remaining-1, speed+1, chosen+(speed,))

    seed = all_windows(v for v in BASE if v not in removed)
    extend(seed, len(removed), Q, ())
    return {"removed": list(removed), "counterexample": None, "counts": counts,
            "limits": limits, "tight": tight}


def audit(ledgers, samples):
    baseline = [(Fraction(j,Q), Fraction(j,Q)) for j in range(1, Q//2+1)]
    check(all_windows(BASE) == baseline, "Tight baseline differs")
    check(not all_windows(range(1, Q+1)), "Strict-cover control did not cover")
    report = []
    for ledger in ledgers:
        records = [json.loads(s) for s in ledger.read_text(encoding="utf-8").splitlines()]
        check(bool(records), "Empty ledger")
        removals = len(records[0]["removed"])
        expected = list(combinations(BASE, removals))
        check([tuple(row["removed"]) for row in records] == expected, "Missing or repeated core")
        totals = Counter()
        maxima = Counter()
        for record in records:
            check(record["counterexample"] is None, "Counterexample needs standalone review")
            counts = record["counts"]
            check(counts[f"nodes_{removals}"] == 1, "Wrong root count")
            for remaining in range(2, removals+1):
                check(counts.get(f"tried_{remaining}", 0) ==
                      counts.get(f"nodes_{remaining-1}", 0), "Child count differs")
            totals.update(counts)
            for key, value in record["limits"].items():
                maxima[key] = max(value, maxima[key])
            for item in record["tight"]:
                speeds = sorted([v for v in BASE if v not in record["removed"]] + item["inserted"])
                check(len(set(speeds)) == Q-1, "Wrong tight set")
                region = all_windows(speeds)
                check(all(a == b for a, b in region)
                      and [str(a) for a, _ in region] == item["times"] and bool(region),
                      "Tight witness differs")

        selected = min(samples, len(records))
        ran = []
        # Use positions spaced over the corpus without ambiguity or random state.
        for i in range(selected):
            index = (i+1)*len(records)//(selected+1)
            check(replay(records[index]["removed"]) == records[index],
                  "Independent replay disagrees with the ledger")
            ran.append(records[index]["removed"])
        item = {"replacements": removals, "base_choices": len(records), "counts": totals,
                "max_limits": maxima, "independent_samples": ran}
        report.append(item)
        print(json.dumps(item, sort_keys=True), flush=True)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ledgers", type=Path, nargs="+")
    parser.add_argument("--sample", type=int, default=1)
    args = parser.parse_args()
    if args.sample < 0:
        parser.error("sample must be nonnegative")
    audit(args.ledgers, args.sample)
