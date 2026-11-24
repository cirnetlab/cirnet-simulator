#ifndef CIRNET_SIMULATOR_WORKER_DC_HPP
#define CIRNET_SIMULATOR_WORKER_DC_HPP

#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <limits>
#include <span>
#include <vector>

namespace cirnet::dc {

struct Potential {
    std::uint32_t node, reference;
    double voltage;
};

struct Resistor {
    std::uint32_t left, right;
    double ohms;
};

struct Driver {
    std::uint32_t signal, node, reference;
    double low, voltage;
};

struct Led {
    std::uint32_t anode, cathode;
    double forward_voltage, max_current;
};

struct DcPlan {
    std::uint32_t node_count = 0;
    std::vector<Potential> potentials;
    std::vector<Resistor> resistors;
    std::vector<std::uint32_t> blockers;
    std::vector<Driver> drivers;
    std::vector<Led> leds;
};

struct LedResult {
    std::uint8_t status;
    double current;
};

namespace detail {

struct Edge {
    std::uint32_t other;
    std::size_t resistor;
    double ohms;
};

enum class Termination { open, known, unknown, unsupported };

struct Trace {
    Termination termination = Termination::open;
    std::uint32_t reference = 0;
    double voltage = 0;
    double resistance = 0;
    bool other_led = false;
};

enum class SourceKind : std::uint8_t { absent, known, conflicting };

struct NodeSource {
    std::uint32_t reference = 0;
    SourceKind kind = SourceKind::absent;
    double voltage = 0;

    void add(std::uint32_t source_reference, double source_voltage) {
        if (kind == SourceKind::absent) {
            reference = source_reference;
            voltage = source_voltage;
            kind = SourceKind::known;
        } else if (reference != source_reference || voltage != source_voltage) {
            kind = SourceKind::conflicting;
        }
    }
};

struct Nodes {
    std::vector<NodeSource> sources;
    std::vector<std::vector<Edge>> edges;
    std::vector<bool> blocked;
    std::vector<bool> unknown;
    std::vector<std::uint32_t> led_users;
};

inline Trace trace(const Nodes& nodes, std::uint32_t node, const Led& led) {
    std::array<std::uint32_t, 9> visited{};
    std::size_t depth = 0;
    std::size_t previous = std::numeric_limits<std::size_t>::max();
    Trace result;
    while (true) {
        const auto visited_end = visited.begin() + depth;
        if (std::find(visited.begin(), visited_end, node) != visited_end || nodes.blocked[node]) {
            result.termination = Termination::unsupported;
            return result;
        }
        visited[depth++] = node;
        const bool this_led_uses_node = node == led.anode || node == led.cathode;
        result.other_led |= nodes.led_users[node] > (this_led_uses_node ? 1U : 0U);

        const Edge* next = nullptr;
        bool branch = false;
        for (const auto& edge : nodes.edges[node]) {
            if (edge.resistor != previous) {
                if (next != nullptr) {
                    branch = true;
                    break;
                }
                next = &edge;
            }
        }
        const auto& source = nodes.sources[node];
        if (source.kind != SourceKind::absent) {
            if (source.kind == SourceKind::conflicting || next != nullptr) {
                result.termination = Termination::unsupported;
            } else {
                result.termination = Termination::known;
                result.reference = source.reference;
                result.voltage = source.voltage;
            }
            return result;
        }
        if (nodes.unknown[node]) {
            result.termination = Termination::unknown;
            return result;
        }
        if (next == nullptr) {
            return result;
        }
        if (branch || depth == visited.size()) {
            result.termination = Termination::unsupported;
            return result;
        }
        previous = next->resistor;
        result.resistance += next->ohms;
        node = next->other;
    }
}

inline LedResult evaluate_led(const Nodes& nodes, const Led& led) {
    const Trace anode = trace(nodes, led.anode, led);
    const Trace cathode = trace(nodes, led.cathode, led);
    if (anode.termination == Termination::unsupported || cathode.termination == Termination::unsupported
        || anode.other_led || cathode.other_led) {
        return {1, 0};
    }
    if (anode.termination == Termination::unknown || cathode.termination == Termination::unknown) {
        return {2, 0};
    }
    if (anode.termination != Termination::known || cathode.termination != Termination::known) {
        return {0, 0};
    }
    if (anode.reference != cathode.reference) {
        return {3, 0};
    }
    const double voltage = anode.voltage - cathode.voltage;
    if (std::abs(voltage) > 6) {
        return {4, 0};
    }
    if (voltage <= led.forward_voltage) {
        return {0, 0};
    }
    const double resistance = anode.resistance + cathode.resistance;
    if (resistance <= 0) {
        return {5, 0};
    }
    const double current = (voltage - led.forward_voltage) / resistance;
    return {static_cast<std::uint8_t>(current <= led.max_current ? 6 : 7), current};
}

}  // namespace detail

inline std::vector<LedResult> solve_dc(const DcPlan& plan, std::span<const std::uint8_t> values) {
    if (plan.leds.empty()) {
        return {};
    }
    detail::Nodes nodes{
        std::vector<detail::NodeSource>(plan.node_count),
        std::vector<std::vector<detail::Edge>>(plan.node_count),
        std::vector<bool>(plan.node_count),
        std::vector<bool>(plan.node_count),
        std::vector<std::uint32_t>(plan.node_count),
    };
    for (const auto& potential : plan.potentials) {
        nodes.sources[potential.node].add(potential.reference, potential.voltage);
    }
    for (const auto& driver : plan.drivers) {
        const std::uint8_t level = values[driver.signal];
        if (level <= 1) {
            nodes.sources[driver.node].add(driver.reference, driver.low + level * driver.voltage);
        } else {
            nodes.unknown[driver.node] = true;
        }
    }
    for (std::size_t index = 0; index < plan.resistors.size(); ++index) {
        const auto& resistor = plan.resistors[index];
        nodes.edges[resistor.left].push_back({resistor.right, index, resistor.ohms});
        nodes.edges[resistor.right].push_back({resistor.left, index, resistor.ohms});
    }
    for (const auto node : plan.blockers) {
        nodes.blocked[node] = true;
    }
    for (const auto& led : plan.leds) {
        ++nodes.led_users[led.anode];
        if (led.cathode != led.anode) {
            ++nodes.led_users[led.cathode];
        }
    }
    std::vector<LedResult> result;
    result.reserve(plan.leds.size());
    for (const auto& led : plan.leds) {
        result.push_back(detail::evaluate_led(nodes, led));
    }
    return result;
}

}  // namespace cirnet::dc

#endif
