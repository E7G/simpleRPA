cmake_minimum_required(VERSION 3.16)
project(simpleRPA LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(SIMPLERPA_WORKSPACE_DIR "${CMAKE_CURRENT_SOURCE_DIR}")

add_custom_target(rust_core ALL
    COMMAND cargo build --release --manifest-path "${SIMPLERPA_WORKSPACE_DIR}/Cargo.toml"
    WORKING_DIRECTORY "${SIMPLERPA_WORKSPACE_DIR}"
    COMMENT "Building Rust core library..."
)

add_subdirectory(gui)
add_dependencies(simpleRPA-gui rust_core)
