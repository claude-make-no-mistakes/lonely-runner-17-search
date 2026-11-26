# Seventeen lonely runners with unbounded speed replacements

Take 16 distinct positive integer speeds relative to a stationary runner. If at least ten speeds belong to $\{1,\ldots,16\}$, the 17-runner Lonely Runner bound holds. The baseline $\{1,\ldots,16\}$ attains exactly $1/17$, and every other set in this family attains a strictly larger distance. The result covers arbitrarily large inserted speeds. [Proof and research note](note.pdf) · [LaTeX](note.tex)

The search accounts for 14,892 retained sets. At every prefix, an interval on which the retained runners are already far enough from the stationary runner gives a bound on the smallest remaining replacement. Each branch therefore has its own exact cutoff. The unrestricted 17-runner conjecture remains open.

| Replacements | Retained sets | Speed trials | Largest exact cutoff |
| --- | ---: | ---: | ---: |
| [1](replace-1.jsonl) | 16 | 72 | 32 |
| [2](replace-2.jsonl) | 120 | 1,899 | 64 |
| [3](replace-3.jsonl) | 560 | 44,575 | 98 |
| [4](replace-4.jsonl) | 1,820 | 826,808 | 141 |
| [5](replace-5.jsonl) | 4,368 | 14,879,151 | 175 |
| [6](replace-6.jsonl) | 8,008 | 346,744,936 | 306 |

Earlier work classifies arbitrary one-entry modifications, treats some unbounded two-entry families, and gives a broader two-entry census with a speed cutoff. The interval-measure argument here sharpens the single-interval bound and applies it recursively. [Zhang, ``6–8](https://arxiv.org/html/2608.13599v3#S6)

## Replay

The Python search uses the standard library and arbitrary-precision integers. The native search uses signed integer arithmetic and a 128-bit intermediate for interval comparisons. It exits with an error if an exact bound exceeds the native arithmetic limit. The observed bounds are in the table above.

    g++ -std=c++17 -O3 -Wall -Wextra -Werror search.cpp -o search
    ./search 6 replay-6.jsonl

Use a matching 64-bit MinGW-w64 executable such as `search.exe` on Windows. The Python search can also regenerate a full ledger. Choose a new output path.

    python search.py replay-4.jsonl --removals 4

The Python and native searches reproduced every row for one to five replacements. The verifier checks census coverage and replays selected rows in independent rational arithmetic, including at six replacements. It also checks the tight baseline and a strict-cover control.

    python verify.py replace-1.jsonl replace-2.jsonl replace-3.jsonl replace-4.jsonl replace-5.jsonl replace-6.jsonl --sample 2
