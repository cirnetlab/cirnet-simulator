cmake_minimum_required(VERSION 3.21)
project(cirnet_simulator LANGUAGES CXX)

add_executable(cirnet-simulator-worker native/worker.cpp)
target_compile_features(cirnet-simulator-worker PRIVATE cxx_std_20)
set_target_properties(cirnet-simulator-worker PROPERTIES CXX_EXTENSIONS OFF)
if(MSVC)
    target_compile_options(cirnet-simulator-worker PRIVATE /W4 /permissive-)
    set_property(TARGET cirnet-simulator-worker PROPERTY MSVC_RUNTIME_LIBRARY
                 "MultiThreaded$<$<CONFIG:Debug>:Debug>")
else()
    target_compile_options(cirnet-simulator-worker PRIVATE -Wall -Wextra -Wpedantic)
endif()

install(TARGETS cirnet-simulator-worker RUNTIME DESTINATION bin)
