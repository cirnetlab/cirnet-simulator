#include <algorithm>
#include <array>
#include <bit>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <limits>
#include <numeric>
#include <queue>
#include <span>
#include <string_view>
#include <vector>

#include "worker_dc.hpp"
#include "worker_limits.hpp"

#ifdef _WIN32
#include <fcntl.h>
#include <io.h>
#endif

namespace {

using Byte = std::uint8_t;
using Signal = std::uint32_t;
using Time = std::uint64_t;

constexpr std::array<Byte, 4> magic_v1{'C', 'N', 'P', '1'};
constexpr std::array<Byte, 4> magic_v2{'C', 'N', 'P', '2'};
constexpr std::uint32_t max_frame_bytes = 16 * 1024 * 1024;
constexpr std::uint32_t max_signals = 131072;
constexpr std::uint32_t max_edges = 131072;
constexpr std::uint32_t max_devices = 8000;
constexpr std::uint32_t max_events = 1000000;
constexpr std::uint32_t max_samples = 100000;
constexpr std::uint32_t max_probes = 4;
constexpr std::uint32_t max_dc_records = 131072;
constexpr Time max_delay_ns = 1000000000;
constexpr Byte unknown = 2;
constexpr Byte unobserved = 3;

constexpr std::size_t request_header_bytes = 52;
constexpr std::size_t response_header_bytes = 25;
constexpr std::size_t edge_bytes = 8;
constexpr std::size_t device_bytes = 21;
constexpr std::size_t event_bytes = 13;
constexpr std::size_t probe_bytes = 4;
constexpr std::size_t dc_header_bytes = 6 * sizeof(std::uint32_t);
constexpr std::size_t dc_potential_bytes = 16;
constexpr std::size_t dc_resistor_bytes = 16;
constexpr std::size_t dc_blocker_bytes = 4;
constexpr std::size_t dc_driver_bytes = 28;
constexpr std::size_t dc_led_bytes = 24;
constexpr std::size_t dc_led_result_bytes = 9;

static_assert(std::numeric_limits<double>::is_iec559 && sizeof(double) == sizeof(std::uint64_t));

enum class Status : Byte { ok, unexecutable, event_limit, capture_limit };
enum class Gate : Byte { and_gate, or_gate, xor_gate, not_gate };

class Reader {
public:
    explicit Reader(std::span<const Byte> bytes) : bytes_(bytes) {}

    // The frame and every record count are checked before reading their fields.
    template <typename Integer>
    Integer next() {
        std::uint64_t value = 0;
        for (std::size_t index = 0; index < sizeof(Integer); ++index) {
            value |= std::uint64_t{bytes_[position_++]} << (index * 8);
        }
        return static_cast<Integer>(value);
    }

    double number() {
        return std::bit_cast<double>(next<std::uint64_t>());
    }

private:
    std::span<const Byte> bytes_;
    std::size_t position_ = 0;
};

template <typename Integer>
void append(std::vector<Byte>& bytes, Integer value) {
    for (std::size_t index = 0; index < sizeof(Integer); ++index) {
        bytes.push_back(static_cast<Byte>(value >> (index * 8)));
    }
}

struct Device {
    Gate gate;
    Signal input_a;
    Signal input_b;
    Signal output;
    Time delay;
    bool enabled;
};

struct Destination {
    Signal signal;
    Byte map_zero;
    Byte map_one;
};

struct Sample {
    Signal signal;
    Time time;
    Byte value;
};

struct Plan {
    Time duration = 0;
    std::uint32_t event_limit = 0;
    std::vector<std::vector<Destination>> destinations;
    std::vector<Device> devices;
    std::vector<Sample> inputs;
    std::vector<Signal> probes;
    cirnet::dc::DcPlan dc;
};

struct DcCounts {
    std::uint32_t potentials = 0;
    std::uint32_t resistors = 0;
    std::uint32_t blockers = 0;
    std::uint32_t drivers = 0;
    std::uint32_t leds = 0;
};

bool read_dc_plan(Reader& reader, const DcCounts& counts, Signal signal_count,
                  cirnet::dc::DcPlan& plan) {
    plan.potentials.reserve(counts.potentials);
    for (std::uint32_t index = 0; index < counts.potentials; ++index) {
        const cirnet::dc::Potential potential{
            reader.next<std::uint32_t>(), reader.next<std::uint32_t>(), reader.number(),
        };
        if (potential.node >= plan.node_count || !std::isfinite(potential.voltage)) {
            return false;
        }
        plan.potentials.push_back(potential);
    }

    plan.resistors.reserve(counts.resistors);
    for (std::uint32_t index = 0; index < counts.resistors; ++index) {
        const cirnet::dc::Resistor resistor{
            reader.next<std::uint32_t>(), reader.next<std::uint32_t>(), reader.number(),
        };
        if (resistor.left >= plan.node_count || resistor.right >= plan.node_count
            || !std::isfinite(resistor.ohms) || resistor.ohms <= 0) {
            return false;
        }
        plan.resistors.push_back(resistor);
    }

    plan.blockers.reserve(counts.blockers);
    for (std::uint32_t index = 0; index < counts.blockers; ++index) {
        const auto node = reader.next<std::uint32_t>();
        if (node >= plan.node_count) {
            return false;
        }
        plan.blockers.push_back(node);
    }

    plan.drivers.reserve(counts.drivers);
    for (std::uint32_t index = 0; index < counts.drivers; ++index) {
        const cirnet::dc::Driver driver{
            reader.next<Signal>(), reader.next<std::uint32_t>(), reader.next<std::uint32_t>(),
            reader.number(), reader.number(),
        };
        if (driver.signal >= signal_count || driver.node >= plan.node_count
            || !std::isfinite(driver.low) || !std::isfinite(driver.voltage)
            || !std::isfinite(driver.low + driver.voltage)) {
            return false;
        }
        plan.drivers.push_back(driver);
    }

    plan.leds.reserve(counts.leds);
    for (std::uint32_t index = 0; index < counts.leds; ++index) {
        const cirnet::dc::Led led{
            reader.next<std::uint32_t>(), reader.next<std::uint32_t>(),
            reader.number(), reader.number(),
        };
        if (led.anode >= plan.node_count || led.cathode >= plan.node_count
            || !std::isfinite(led.forward_voltage) || led.forward_voltage < 0
            || !std::isfinite(led.max_current) || led.max_current <= 0) {
            return false;
        }
        plan.leds.push_back(led);
    }
    return true;
}

bool read_plan(Reader& reader, std::size_t body_size, bool with_dc, Plan& plan) {
    plan.duration = reader.next<Time>();
    plan.event_limit = reader.next<std::uint32_t>();
    const auto signal_count = reader.next<std::uint32_t>();
    const auto edge_count = reader.next<std::uint32_t>();
    const auto device_count = reader.next<std::uint32_t>();
    const auto input_count = reader.next<std::uint32_t>();
    const auto probe_count = reader.next<std::uint32_t>();

    DcCounts dc_counts;
    if (with_dc) {
        if (body_size < request_header_bytes + dc_header_bytes) {
            return false;
        }
        plan.dc.node_count = reader.next<std::uint32_t>();
        dc_counts = {
            reader.next<std::uint32_t>(), reader.next<std::uint32_t>(), reader.next<std::uint32_t>(),
            reader.next<std::uint32_t>(), reader.next<std::uint32_t>(),
        };
        if (std::max({plan.dc.node_count, dc_counts.potentials, dc_counts.resistors,
                      dc_counts.blockers, dc_counts.drivers, dc_counts.leds}) > max_dc_records) {
            return false;
        }
    }

    const auto expected_size = request_header_bytes
        + (with_dc ? dc_header_bytes : 0)
        + std::uint64_t{edge_count} * (edge_bytes + (with_dc ? 2 : 0))
        + std::uint64_t{device_count} * (device_bytes + (with_dc ? 1 : 0))
        + std::uint64_t{input_count} * event_bytes
        + std::uint64_t{probe_count} * probe_bytes
        + std::uint64_t{dc_counts.potentials} * dc_potential_bytes
        + std::uint64_t{dc_counts.resistors} * dc_resistor_bytes
        + std::uint64_t{dc_counts.blockers} * dc_blocker_bytes
        + std::uint64_t{dc_counts.drivers} * dc_driver_bytes
        + std::uint64_t{dc_counts.leds} * dc_led_bytes;
    if (body_size != expected_size || signal_count > max_signals
        || edge_count > max_edges || device_count > max_devices || probe_count > max_probes
        || plan.event_limit == 0 || plan.event_limit > max_events) {
        return false;
    }

    plan.destinations.resize(signal_count);
    std::vector<bool> has_driver(signal_count);
    for (std::uint32_t index = 0; index < edge_count; ++index) {
        const auto source = reader.next<Signal>();
        const auto destination = reader.next<Signal>();
        const auto map_zero = with_dc ? reader.next<Byte>() : Byte{0};
        const auto map_one = with_dc ? reader.next<Byte>() : Byte{1};
        if (source >= signal_count || destination >= signal_count || source == destination
            || has_driver[destination] || map_zero > unknown || map_one > unknown) {
            return false;
        }
        has_driver[destination] = true;
        plan.destinations[source].push_back({destination, map_zero, map_one});
    }

    plan.devices.reserve(device_count);
    std::vector<bool> has_device_output(signal_count);
    for (std::uint32_t index = 0; index < device_count; ++index) {
        const auto gate = static_cast<Gate>(reader.next<Byte>());
        const auto input_a = reader.next<Signal>();
        const auto input_b = reader.next<Signal>();
        const auto output = reader.next<Signal>();
        const auto delay = reader.next<Time>();
        const auto enabled = with_dc ? reader.next<Byte>() : Byte{1};
        if (gate > Gate::not_gate || input_a >= signal_count || output >= signal_count
            || (gate == Gate::not_gate ? input_b != 0 : input_b >= signal_count)
            || delay > max_delay_ns || enabled > 1 || has_device_output[output] || has_driver[output]) {
            return false;
        }
        has_device_output[output] = true;
        plan.devices.push_back({gate, input_a, input_b, output, delay, enabled != 0});
    }

    plan.inputs.reserve(input_count);
    for (std::uint32_t index = 0; index < input_count; ++index) {
        const auto time = reader.next<Time>();
        const auto signal = reader.next<Signal>();
        const auto value = reader.next<Byte>();
        if (time > plan.duration || signal >= signal_count || value > 1
            || has_device_output[signal]) {
            return false;
        }
        plan.inputs.push_back({signal, time, value});
    }

    plan.probes.reserve(probe_count);
    for (std::uint32_t index = 0; index < probe_count; ++index) {
        const auto signal = reader.next<Signal>();
        if (signal >= signal_count
            || std::find(plan.probes.begin(), plan.probes.end(), signal) != plan.probes.end()) {
            return false;
        }
        plan.probes.push_back(signal);
    }
    return !with_dc || read_dc_plan(reader, dc_counts, signal_count, plan.dc);
}

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

bool write_response(const std::array<Byte, 4>& magic, std::uint64_t request,
                    std::uint64_t generation, Status status, std::span<const Sample> capture,
                    std::span<const Byte> values, std::span<const cirnet::dc::LedResult> leds) {
    if (status != Status::ok) {
        capture = {};
    }
    const bool with_dc = magic == magic_v2 && status == Status::ok;
    const auto dc_size = with_dc ? 2 * sizeof(std::uint32_t) + values.size()
        + leds.size() * dc_led_result_bytes : 0;
    const auto body_size = response_header_bytes + capture.size() * event_bytes + dc_size;
    std::vector<Byte> response;
    response.reserve(sizeof(std::uint32_t) + body_size);
    append(response, static_cast<std::uint32_t>(body_size));
    response.insert(response.end(), magic.begin(), magic.end());
    append(response, request);
    append(response, generation);
    append(response, static_cast<Byte>(status));
    append(response, static_cast<std::uint32_t>(capture.size()));
    for (const auto& sample : capture) {
        append(response, sample.signal);
        append(response, sample.time);
        append(response, sample.value);
    }
    if (with_dc) {
        append(response, static_cast<std::uint32_t>(values.size()));
        response.insert(response.end(), values.begin(), values.end());
        append(response, static_cast<std::uint32_t>(leds.size()));
        for (const auto& led : leds) {
            append(response, led.status);
            append(response, std::bit_cast<std::uint64_t>(led.current));
        }
    }
    return std::fwrite(response.data(), 1, response.size(), stdout) == response.size()
        && std::fflush(stdout) == 0;
}

}  // namespace

int main(int argc, char* argv[]) {
    const bool persistent = argc == 2 && std::string_view{argv[1]} == "--serve";
    if ((argc != 1 && !persistent) || !apply_worker_limits()) {
        return 1;
    }
#ifdef _WIN32
    if (_setmode(_fileno(stdin), _O_BINARY) == -1 || _setmode(_fileno(stdout), _O_BINARY) == -1) {
        return 1;
    }
#endif
    for (;;) {
        std::array<Byte, sizeof(std::uint32_t)> prefix{};
        const auto prefix_bytes = std::fread(prefix.data(), 1, prefix.size(), stdin);
        if (prefix_bytes != prefix.size()) {
            // In serve mode, EOF is clean only between complete requests.
            return persistent && prefix_bytes == 0 && std::feof(stdin) && !std::ferror(stdin) ? 0 : 1;
        }
        const auto size = Reader{prefix}.next<std::uint32_t>();
        if (size < request_header_bytes || size > max_frame_bytes) {
            return 1;
        }
        std::vector<Byte> body(size);
        if (std::fread(body.data(), 1, body.size(), stdin) != body.size()) {
            return 1;
        }
        const bool with_dc = std::equal(magic_v2.begin(), magic_v2.end(), body.begin());
        if (!with_dc && !std::equal(magic_v1.begin(), magic_v1.end(), body.begin())) {
            return 1;
        }
        if (!persistent && (std::fgetc(stdin) != EOF || std::ferror(stdin))) {
            return 1;
        }
        const auto& magic = with_dc ? magic_v2 : magic_v1;
        Reader reader{std::span<const Byte>{body}.subspan(magic.size())};
        const auto request = reader.next<std::uint64_t>();
        const auto generation = reader.next<std::uint64_t>();
        Plan plan;
        std::vector<Sample> capture;
        std::vector<Byte> values;
        auto status = read_plan(reader, body.size(), with_dc, plan)
            ? simulate(plan, capture, values)
            : Status::unexecutable;
        std::vector<cirnet::dc::LedResult> leds;
        if (with_dc && status == Status::ok) {
            leds = cirnet::dc::solve_dc(plan.dc, values);
            if (leds.size() != plan.dc.leds.size()
                || std::any_of(leds.begin(), leds.end(), [](const auto& led) {
                    return led.status > 7 || !std::isfinite(led.current) || led.current < 0;
                })) {
                status = Status::unexecutable;
            }
        }
        if (!write_response(magic, request, generation, status, capture, values, leds)) {
            return 1;
        }
        if (!persistent) {
            return 0;
        }
    }
}
