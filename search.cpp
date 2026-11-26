#include <algorithm>
#include <array>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <limits>
#include <numeric>
#include <stdexcept>
#include <string>
#include <vector>

using Int = std::int64_t;
using Wide = __int128;
constexpr Int runners = 17;
constexpr Int safe_speed = 1'000'000;

struct Point {
    Int numerator, denominator;
};

bool operator<(Point a, Point b) {
    return a.numerator * b.denominator < b.numerator * a.denominator;
}

struct Interval {
    Point left, right;
};

using Region = std::vector<Interval>;

Int floor_div(Int a, Int b) {
    return a >= 0 ? a / b : -((-a + b - 1) / b);
}

Int ceil_div(Int a, Int b) {
    return -floor_div(-a, b);
}

void retain(const Region& domain, Int speed, Region& output) {
    output.clear();
    for (const auto& [left, right] : domain) {
        const auto [a, b] = left;
        const auto [c, d] = right;
        const Int first = ceil_div(speed*a - (runners-1)*b, runners*b);
        const Int last = floor_div(speed*c - d, runners*d);
        for (Int k = first; k <= last; ++k) {
            const auto lo = std::max(left, Point{runners*k+1, speed});
            const auto hi = std::min(right, Point{runners*k+runners-1, speed});
            if (!(hi < lo)) {
                output.push_back({lo, hi});
            }
        }
    }
}

bool can_cover(Int speed, const Region& region, unsigned widest) {
    const auto fits = [speed](const Interval& interval) {
        const auto [a, b] = interval.left;
        const auto [c, d] = interval.right;
        return ceil_div(speed*c - d, runners*d) <= floor_div(speed*a + b, runners*b);
    };
    if (!fits(region[widest])) {
        return false;
    }
    for (unsigned i = 0; i < region.size(); ++i) {
        const auto& interval = region[i];
        if (i != widest && interval.left < interval.right && !fits(interval)) {
            return false;
        }
    }
    return true;
}

struct Tight {
    std::vector<Int> prefix;
    std::vector<std::string> times;
};

class Search {
public:
    Search(int replacements, std::ostream& output)
        : replacements(replacements), output(output) {}

    void roots(int next) {
        if (removed.size() == static_cast<unsigned>(replacements)) {
            run_one();
            return;
        }
        const Int missing = replacements - static_cast<Int>(removed.size());
        for (int v = next; v < runners && runners-v >= missing; ++v) {
            removed.push_back(v);
            roots(v+1);
            removed.pop_back();
        }
    }

private:
    int replacements;
    std::ostream& output;
    std::vector<int> removed;
    std::vector<Int> prefix;
    std::array<Region, 9> regions;
    std::array<Int, 9> nodes{}, tried{}, limits{};
    std::vector<Tight> tight;

    static void increment(Int& counter) {
        if (counter == std::numeric_limits<Int>::max()) {
            throw std::runtime_error("native count exceeds integer range");
        }
        ++counter;
    }

    void explore(int remaining, Int low) {
        const auto& region = regions[remaining];
        Int largest = 0, denominator = 1;
        unsigned widest = 0;
        for (unsigned i = 0; i < region.size(); ++i) {
            const auto [a, b] = region[i].left;
            const auto [c, d] = region[i].right;
            const Int length = c*b-a*d;
            if (Wide(length)*denominator > Wide(largest)*b*d) {
                largest = length;
                denominator = b*d;
                widest = i;
            }
        }
        if (!largest && (remaining || region.empty())) {
            // This prefix is a potential counterexample. The Python search
            // reconstructs the witness even if a common multiple is huge.
            std::cerr << "Recheck removed speeds";
            for (auto value : removed) {
                std::cerr << ' ' << value;
            }
            throw std::runtime_error(" with arbitrary-precision search");
        }
        if (!remaining) {
            if (largest) {
                throw std::runtime_error("terminal pruning disagrees with interval intersection");
            }
            auto& entry = tight.emplace_back();
            entry.prefix = prefix;
            for (const auto& interval : region) {
                const auto [a, b] = interval.left;
                const Int divisor = std::gcd(a, runners*b);
                entry.times.push_back(std::to_string(a/divisor) + "/" +
                                      std::to_string(runners*b/divisor));
            }
            return;
        }
        const Int bound = remaining == 1 ? 2*denominator/largest
            : 2*remaining*(runners-2)*denominator/((runners-2*remaining)*largest);
        increment(nodes[remaining]);
        limits[remaining] = std::max(limits[remaining], bound);
        if (bound > safe_speed) {
            throw std::runtime_error("speed bound exceeds the native arithmetic limit");
        }
        for (Int speed = low; speed <= bound; ++speed) {
            increment(tried[remaining]);
            if (remaining > 1 || can_cover(speed, region, widest)) {
                retain(region, speed, regions[remaining-1]);
                prefix.push_back(speed);
                explore(remaining-1, speed+1);
                prefix.pop_back();
            }
        }
    }

    template<class Values>
    void array(const Values& values) {
        output << '[';
        for (unsigned i = 0; i < values.size(); ++i) {
            if (i != 0) {
                output << ',';
            }
            output << values[i];
        }
        output << ']';
    }

    void run_one() {
        nodes.fill(0);
        tried.fill(0);
        limits.fill(0);
        tight.clear();
        Region region{{{0, 1}, {runners, 2}}}, scratch;
        for (int v = 1; v < runners; ++v) {
            if (!std::binary_search(removed.begin(), removed.end(), v)) {
                retain(region, v, scratch);
                region.swap(scratch);
            }
        }
        regions[replacements].swap(region);
        explore(replacements, runners);
        output << "{\"removed\":";
        array(removed);
        output << ",\"counterexample\":null,\"counts\":{";
        bool first = true;
        for (int i = 1; i <= replacements; ++i) {
            for (const auto& [key, value] : {std::pair{"nodes_", nodes[i]},
                                             std::pair{"tried_", tried[i]}}) {
                if (value) {
                    output << (first ? "\"" : ",\"") << key << i << "\":" << value;
                    first = false;
                }
            }
        }
        if (!tight.empty()) {
            output << ",\"tight\":" << tight.size();
        }
        output << "},\"limits\":{";
        first = true;
        for (int i = 1; i <= replacements; ++i) {
            if (nodes[i] != 0) {
                output << (first ? "\"" : ",\"") << i << "\":" << limits[i];
                first = false;
            }
        }
        output << "},\"tight\":[";
        for (unsigned i = 0; i < tight.size(); ++i) {
            output << (i == 0 ? "" : ",") << "{\"inserted\":";
            array(tight[i].prefix);
            output << ",\"times\":[";
            for (unsigned j = 0; j < tight[i].times.size(); ++j) {
                output << (j == 0 ? "\"" : ",\"") << tight[i].times[j] << '"';
            }
            output << "]}";
        }
        output << "]}\n";
        output.flush();
    }
};

int main(int argc, char** argv) {
    try {
        if (argc != 3) {
            throw std::runtime_error("usage: search <replacements> <new output>");
        }
        const int count = std::stoi(argv[1]);
        if (count < 1 || count > runners/2) {
            throw std::runtime_error("expected between one and eight replacements");
        }
        if (std::ifstream(argv[2])) {
            throw std::runtime_error("output already exists");
        }
        std::ofstream output(argv[2], std::ios::binary);
        output.exceptions(std::ios::badbit | std::ios::failbit);
        Search(count, output).roots(1);
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
