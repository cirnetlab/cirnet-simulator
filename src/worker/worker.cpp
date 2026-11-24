#include <algorithm>
#include <array>
#include <bit>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <limits>
#include <span>
#include <string_view>
#include <vector>

#include "worker_dc.hpp"
#include "worker_digital.hpp"
#include "worker_limits.hpp"

#ifdef _WIN32
#include <fcntl.h>
#include <io.h>
#endif

namespace {

using cirnet::digital::Byte;
using cirnet::digital::Gate;
using cirnet::digital::Plan;
using cirnet::digital::Sample;
using cirnet::digital::Signal;
using cirnet::digital::Status;
using cirnet::digital::Time;
using cirnet::digital::unknown;

constexpr std::array<Byte, 4> magic_v1{'C', 'N', 'P', '1'};
constexpr std::array<Byte, 4> magic_v2{'C', 'N', 'P', '2'};
constexpr std::uint32_t max_frame_bytes = 16 * 1024 * 1024;
constexpr std::uint32_t max_signals = 131072;
constexpr std::uint32_t max_edges = 131072;
constexpr std::uint32_t max_devices = 8000;
constexpr std::uint32_t max_events = 1000000;
constexpr std::uint32_t max_probes = 4;
constexpr std::uint32_t max_dc_records = 131072;
constexpr Time max_delay_ns = 1000000000;

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

bool read_plan(Reader& reader, std::size_t body_size, bool with_dc, Plan& plan,
               cirnet::dc::DcPlan& dc) {
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
        dc.node_count = reader.next<std::uint32_t>();
        dc_counts = {
            reader.next<std::uint32_t>(), reader.next<std::uint32_t>(), reader.next<std::uint32_t>(),
            reader.next<std::uint32_t>(), reader.next<std::uint32_t>(),
        };
        if (std::max({dc.node_count, dc_counts.potentials, dc_counts.resistors,
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
    return !with_dc || read_dc_plan(reader, dc_counts, signal_count, dc);
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
    if (argc == 2 && std::string_view{argv[1]} == "--version") {
        return std::puts("cirnet-simulator-worker " CIRNET_SIMULATOR_VERSION) < 0 ? 1 : 0;
    }
    if (argc == 2 && std::string_view{argv[1]} == "--protocols") {
        return std::puts("CNP1\nCNP2") < 0 ? 1 : 0;
    }
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
        cirnet::dc::DcPlan dc;
        std::vector<Sample> capture;
        std::vector<Byte> values;
        auto status = read_plan(reader, body.size(), with_dc, plan, dc)
            ? cirnet::digital::simulate(plan, capture, values)
            : Status::unexecutable;
        std::vector<cirnet::dc::LedResult> leds;
        if (with_dc && status == Status::ok) {
            leds = cirnet::dc::solve_dc(dc, values);
            if (leds.size() != dc.leds.size()
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
