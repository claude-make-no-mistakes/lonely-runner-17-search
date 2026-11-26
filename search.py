"""Search all possible large replacements of one to several of the speeds 1..16."""

import argparse
from collections import Counter
from fractions import Fraction
from itertools import combinations
import json
from math import lcm
from pathlib import Path


N = 17
# Each tuple stores the two scaled endpoints Nt as unreduced fractions.
HALF = [(0, 1, N, 2)]


def retain(region, speed):
    good = []
    for a, b, c, d in region:
        first = -((N*b - b - speed*a) // (N*b))
        last = (speed*c - d) // (N*d)
        for k in range(first, last + 1):
            left, right = N*k+1, N*k+N-1
            lo, den_lo = (a, b) if a*speed >= left*b else (left, speed)
            hi, den_hi = (c, d) if c*speed <= right*d else (right, speed)
            if lo*den_hi <= hi*den_lo:
                good.append((lo, den_lo, hi, den_hi))
    return good


def final_possible(speed, positive):
    # A positive interval must fit completely in one closed bad arc.
    for a, b, c, d in positive:
        if -((d - speed*c) // (N*d)) > (speed*a + b) // (N*b):
            return False
    return True


def first_bound(remaining, interval):
    a, b, c, d = interval
    width = c*b - a*d
    if remaining == 1:
        return (2*b*d) // width
    return (2*remaining*(N-2)*b*d) // ((N-2*remaining)*width)


def widest_interval(positive):
    widest = positive[0]
    a, b, c, d = widest
    width, denominator = c*b - a*d, b*d
    for interval in positive[1:]:
        a, b, c, d = interval
        if (c*b - a*d)*denominator > width*b*d:
            widest = interval
            width, denominator = c*b - a*d, b*d
    return widest


def extinguish(region, low, remaining):
    # A prefix with only finitely many threshold times already refutes
    # the full statement after appending a speed vanishing at all those times.
    period = lcm(*(Fraction(a, N*b).denominator for a, b, _, _ in region))
    start = (low + period - 1) // period
    return tuple(period * (start+i) for i in range(remaining))


def explore(region, remaining, low, prefix, counts, maxima, tight):
    positive = [(a, b, c, d) for a, b, c, d in region if c*b > a*d]
    if not positive:
        if remaining:
            return prefix + extinguish(region, low, remaining)
        if region:
            times = [str(Fraction(a, N*b)) for a, b, _, _ in region]
            tight.append({"inserted": prefix, "times": times})
            counts["tight"] += 1
            return None
        return prefix
    if not remaining:
        raise ValueError("A terminal node should have been prefiltered")
    # Put the longest interval first in the last-speed rejection test.
    widest = widest_interval(positive)
    limit = first_bound(remaining, widest)
    counts[f"nodes_{remaining}"] += 1
    maxima[remaining] = max(maxima[remaining], limit)
    if remaining > 1:
        for speed in range(low, limit+1):
            counts[f"tried_{remaining}"] += 1
            found = explore(retain(region, speed), remaining-1, speed+1,
                            prefix + (speed,), counts, maxima, tight)
            if found is not None:
                return found
        return None

    ordered = [widest, *(interval for interval in positive if interval != widest)]
    for speed in range(low, limit+1):
        counts["tried_1"] += 1
        if final_possible(speed, ordered):
            found = explore(retain(region, speed), 0, speed+1, prefix + (speed,),
                            counts, maxima, tight)
            if found is not None:
                return found
    return None


def search(removals, output):
    baseline = tuple(range(1, N))
    totals = Counter()
    record_count = 0
    with output.open("x", encoding="utf-8", newline="\n") as ledger:
        for removed in combinations(baseline, removals):
            retained = tuple(v for v in baseline if v not in removed)
            region = HALF
            for speed in retained:
                region = retain(region, speed)
            counts = Counter()
            maxima = Counter()
            tight = []
            witness = explore(region, removals, N, (), counts, maxima, tight)
            row = {"removed": removed, "counts": counts, "limits": maxima, "tight": tight,
                   "counterexample": sorted(retained + witness) if witness is not None else None}
            ledger.write(json.dumps(row, separators=(",", ":"), sort_keys=True) + "\n")
            record_count += 1
            totals.update(counts)
            if witness is not None:
                print(json.dumps(row), flush=True)
                break
            if record_count % 250 == 0:
                print(f"Completed {record_count} retained sets", flush=True)
    print(json.dumps({"records": record_count, "removals": removals, "totals": totals},
                     sort_keys=True), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--removals", type=int, required=True)
    args = parser.parse_args()
    if not 1 <= args.removals < N/2:
        parser.error("expected between one and eight replacements")
    search(args.removals, args.output)
