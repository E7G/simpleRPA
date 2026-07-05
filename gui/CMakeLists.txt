cmake_minimum_required(VERSION 3.15)
project(SimpleRPA VERSION 0.2.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_AUTOMOC ON)
set(CMAKE_AUTORCC ON)
set(CMAKE_AUTOUIC ON)

# Qt configuration
find_package(Qt5 REQUIRED COMPONENTS Core Widgets Svg Xml)

# QFluentKit
find_package(QFluent REQUIRED)

# Rust static library
set(RUST_LIB_DIR "${CMAKE_SOURCE_DIR}/../target/release")
set(RUST_LIB_NAME "simplerpa_ffi")

if(WIN32)
    set(RUST_LIB_FILE "${RUST_LIB_DIR}/${RUST_LIB_NAME}.dll")
    set(RUST_IMPLIB_FILE "${RUST_LIB_DIR}/${RUST_LIB_NAME}.lib")
elseif(UNIX AND NOT APPLE)
    set(RUST_LIB_FILE "${RUST_LIB_DIR}/lib${RUST_LIB_NAME}.so")
else()
    set(RUST_LIB_FILE "${RUST_LIB_DIR}/lib${RUST_LIB_NAME}.dylib")
endif()

# Source files
set(SOURCES
    src/main.cpp
    src/main_window.cpp
    src/ffi/rpa_bridge.cpp
    src/panels/action_panel.cpp
    src/panels/property_panel.cpp
    src/panels/recorder_panel.cpp
    src/panels/script_editor.cpp
    src/panels/window_selector.cpp
    src/panels/dashboard_page.cpp
    src/panels/command_panel.cpp
)

set(HEADERS
    src/main_window.h
    src/ffi/rpa_bridge.h
    src/panels/action_panel.h
    src/panels/property_panel.h
    src/panels/recorder_panel.h
    src/panels/script_editor.h
    src/panels/window_selector.h
    src/panels/dashboard_page.h
    src/panels/command_panel.h
)

# Create executable
add_executable(${PROJECT_NAME} WIN32 ${SOURCES} ${HEADERS})

target_include_directories(${PROJECT_NAME} PRIVATE
    ${CMAKE_SOURCE_DIR}/../include
    ${CMAKE_CURRENT_SOURCE_DIR}/src
)

target_link_directories(${PROJECT_NAME} PRIVATE ${RUST_LIB_DIR})

if(WIN32)
    target_link_libraries(${PROJECT_NAME} PRIVATE
        Qt5::Core Qt5::Widgets Qt5::Svg Qt5::Xml
        QFluent::QFluent
        ${RUST_IMPLIB_FILE}
    )
else()
    target_link_libraries(${PROJECT_NAME} PRIVATE
        Qt5::Core Qt5::Widgets Qt5::Svg Qt5::Xml
        QFluent::QFluent
        ${RUST_LIB_FILE}
    )
endif()

# Copy Rust DLL to output directory
add_custom_command(TARGET ${PROJECT_NAME} POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E copy_if_different
        "${RUST_LIB_FILE}"
        "$<TARGET_FILE_DIR:${PROJECT_NAME}>"
)
