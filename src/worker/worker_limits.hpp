#ifndef CIRNET_SIMULATOR_WORKER_LIMITS_HPP
#define CIRNET_SIMULATOR_WORKER_LIMITS_HPP

#include <cstddef>

#if defined(_WIN32)
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>
#elif defined(__unix__) || defined(__APPLE__)
#include <sys/resource.h>
#endif

inline bool apply_worker_limits() {
    constexpr std::size_t memory_limit = 256U * 1024U * 1024U;
#if defined(_WIN32)
    const HANDLE job = CreateJobObjectW(nullptr, nullptr);
    if (job == nullptr) {
        return false;
    }
    JOBOBJECT_EXTENDED_LIMIT_INFORMATION limits{};
    limits.BasicLimitInformation.LimitFlags =
        JOB_OBJECT_LIMIT_PROCESS_MEMORY | JOB_OBJECT_LIMIT_ACTIVE_PROCESS;
    limits.BasicLimitInformation.ActiveProcessLimit = 1;
    limits.ProcessMemoryLimit = memory_limit;
    const bool attached =
        SetInformationJobObject(job, JobObjectExtendedLimitInformation, &limits, sizeof(limits))
        && AssignProcessToJobObject(job, GetCurrentProcess());
    // With no kill-on-close flag, the job continues to limit its associated worker.
    CloseHandle(job);
    return attached;
#elif defined(RLIMIT_AS)
    rlimit limits{};
    if (getrlimit(RLIMIT_AS, &limits) != 0) {
        return false;
    }
    if (limits.rlim_cur <= memory_limit) {
        return true;
    }
    limits.rlim_cur = memory_limit;
    return setrlimit(RLIMIT_AS, &limits) == 0;
#else
    return false;
#endif
}

#endif
