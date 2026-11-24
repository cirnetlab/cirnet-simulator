#include "worker_digital.hpp"

#include <algorithm>
#include <limits>
#include <numeric>
#include <queue>

namespace cirnet::digital {
namespace {

constexpr std::uint32_t max_samples = 100000;
constexpr Byte unobserved = 3;

struct Event {
    Sample sample;
    std::uint32_t sequence;
};

struct LaterEvent {
    bool operator()(const Event& left, const Event& right) const {
        if (left.sample.time != right.sample.time) {
            return left.sample.time > right.sample.time;
        }
        return left.sequence > right.sequence;
    }
};

Byte evaluate(const Device& device, const std::vector<Byte>& values) {
    const Byte a = values[device.input_a];
    const Byte b = values[device.input_b];
    switch (device.gate) {
    case Gate::and_gate:
        return a == 0 || b == 0 ? 0 : (a == 1 && b == 1 ? 1 : unknown);
    case Gate::or_gate:
        return a == 1 || b == 1 ? 1 : (a == 0 && b == 0 ? 0 : unknown);
    case Gate::xor_gate:
        return a == unknown || b == unknown ? unknown : static_cast<Byte>(a ^ b);
    case Gate::not_gate:
        return a == unknown ? unknown : static_cast<Byte>(1 - a);
    }
    return unknown;
}

}  // namespace

Status simulate(const Plan& plan, std::vector<Sample>& capture, std::vector<Byte>& values) {
    std::priority_queue<Event, std::vector<Event>, LaterEvent> queue;
    std::uint32_t sequence = 0;
    auto enqueue = [&](const Sample& sample) {
        if (sequence == plan.event_limit) {
            return false;
        }
        queue.push({sample, sequence++});
        return true;
    };
    for (const auto& input : plan.inputs) {
        if (!enqueue(input)) {
            return Status::event_limit;
        }
    }

    values.assign(plan.destinations.size(), unknown);
    std::vector<std::vector<std::uint32_t>> dependencies(values.size());
    std::vector<std::uint32_t> affected(plan.devices.size());
    std::iota(affected.begin(), affected.end(), std::uint32_t{0});
    std::vector<bool> marked(plan.devices.size(), true);
    for (const auto index : affected) {
        const auto& device = plan.devices[index];
        dependencies[device.input_a].push_back(index);
        if (device.gate != Gate::not_gate && device.input_a != device.input_b) {
            dependencies[device.input_b].push_back(index);
        }
    }
    std::vector<Byte> last(plan.probes.size(), unobserved);

    Time timestamp = 0;
    for (;;) {
        while (!queue.empty() && queue.top().sample.time == timestamp) {
            const auto [signal, time, value] = queue.top().sample;
            queue.pop();
            if (values[signal] == value) {
                continue;
            }
            values[signal] = value;
            for (const auto device : dependencies[signal]) {
                if (!marked[device]) {
                    marked[device] = true;
                    affected.push_back(device);
                }
            }
            for (const auto& destination : plan.destinations[signal]) {
                const auto mapped = value == 0 ? destination.map_zero
                    : (value == 1 ? destination.map_one : unknown);
                if (!enqueue({destination.signal, time, mapped})) {
                    return Status::event_limit;
                }
            }
        }

        std::sort(affected.begin(), affected.end());
        for (const auto index : affected) {
            const auto& device = plan.devices[index];
            if (device.delay > std::numeric_limits<Time>::max() - timestamp) {
                return Status::unexecutable;
            }
            const auto value = device.enabled ? evaluate(device, values) : unknown;
            if (!enqueue({device.output, timestamp + device.delay, value})) {
                return Status::event_limit;
            }
            marked[index] = false;
        }
        affected.clear();

        // Process zero-delay outputs and any propagation they trigger before sampling.
        if (!queue.empty() && queue.top().sample.time == timestamp) {
            continue;
        }
        for (std::size_t index = 0; index < plan.probes.size(); ++index) {
            const auto signal = plan.probes[index];
            if (last[index] != values[signal]) {
                if (capture.size() == max_samples) {
                    return Status::capture_limit;
                }
                last[index] = values[signal];
                capture.push_back({signal, timestamp, values[signal]});
            }
        }
        if (queue.empty() || queue.top().sample.time > plan.duration) {
            return Status::ok;
        }
        timestamp = queue.top().sample.time;
    }
}

}  // namespace cirnet::digital
