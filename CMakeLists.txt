cmake_minimum_required(VERSION 3.21)
project(cirnet_simulator VERSION 0.3.0 LANGUAGES CXX)

add_executable(cirnet-simulator-worker
    src/worker/worker.cpp
    src/worker/worker_digital.cpp
)
target_compile_features(cirnet-simulator-worker PRIVATE cxx_std_20)
target_compile_definitions(cirnet-simulator-worker PRIVATE CIRNET_SIMULATOR_VERSION="${PROJECT_VERSION}-dev.1")
set_target_properties(cirnet-simulator-worker PROPERTIES CXX_EXTENSIONS OFF)
if(MSVC)
    target_compile_options(cirnet-simulator-worker PRIVATE /W4 /permissive-)
    set_property(TARGET cirnet-simulator-worker PROPERTY MSVC_RUNTIME_LIBRARY
                 "MultiThreaded$<$<CONFIG:Debug>:Debug>")
else()
    target_compile_options(cirnet-simulator-worker PRIVATE -Wall -Wextra -Wpedantic)
endif()

install(TARGETS cirnet-simulator-worker RUNTIME DESTINATION bin)
