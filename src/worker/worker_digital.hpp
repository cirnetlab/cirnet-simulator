#ifndef CIRNET_SIMULATOR_WORKER_DIGITAL_HPP
#define CIRNET_SIMULATOR_WORKER_DIGITAL_HPP

#include <cstdint>
#include <vector>

namespace cirnet::digital {

using Byte = std::uint8_t;
using Signal = std::uint32_t;
using Time = std::uint64_t;

inline constexpr Byte unknown = 2;

enum class Status : Byte { ok, unexecutable, event_limit, capture_limit };
enum class Gate : Byte { and_gate, or_gate, xor_gate, not_gate };

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
};

Status simulate(const Plan& plan, std::vector<Sample>& capture, std::vector<Byte>& values);

}  // namespace cirnet::digital

#endif
