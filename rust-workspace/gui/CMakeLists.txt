cmake_minimum_required(VERSION 3.16)
project(simpleRPA-gui LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_AUTOMOC ON)
set(CMAKE_AUTORCC ON)
set(CMAKE_AUTOUIC ON)

find_package(Qt6 QUIET COMPONENTS Core Widgets Svg Xml)
if(Qt6_FOUND)
    set(QT_PACKAGE_PREFIX Qt6)
else()
    find_package(Qt5 5.12 REQUIRED COMPONENTS Core Widgets Svg Xml)
    set(QT_PACKAGE_PREFIX Qt5)
endif()

add_subdirectory(qfluentkit/QFluent)

set(RUST_LIB_DIR "${CMAKE_SOURCE_DIR}/target/release")
add_library(simpleRPA_core STATIC IMPORTED)
set_target_properties(simpleRPA_core PROPERTIES
    IMPORTED_LOCATION "${RUST_LIB_DIR}/simpleRPA_core.lib"
    IMPORTED_IMPLIB "${RUST_LIB_DIR}/simpleRPA_core.lib"
)

include_directories(${CMAKE_CURRENT_SOURCE_DIR}/include)
include_directories(${CMAKE_CURRENT_SOURCE_DIR}/qfluentkit/QFluent/src)
include_directories(${CMAKE_CURRENT_SOURCE_DIR}/src)

set(SOURCES
    src/main.cpp
    src/main_window.cpp
    src/FluentWidget.cpp
    src/FluentTitleBar.cpp
    src/action_panel.cpp
    src/action_list_row.cpp
    src/property_panel.cpp
    src/recorder_panel.cpp
    src/command_panel.cpp
    src/dashboard_page.cpp
    src/script_editor.cpp
    src/preview_overlay.cpp
    src/tray_service.cpp
    src/window_selector.cpp
    res/res.qrc
)

set(HEADERS
    src/main_window.h
    src/FluentWidget.h
    src/FluentTitleBar.h
    src/action_panel.h
    src/action_list_row.h
    src/property_panel.h
    src/recorder_panel.h
    src/command_panel.h
    src/dashboard_page.h
    src/script_editor.h
    src/preview_overlay.h
    src/tray_service.h
    src/window_selector.h
    src/fluent_theme.h
    include/simpleRPA_ffi.h
)

add_executable(simpleRPA-gui WIN32 MACOSX_BUNDLE ${SOURCES} ${HEADERS})

target_link_libraries(simpleRPA-gui PRIVATE
    ${QT_PACKAGE_PREFIX}::Core
    ${QT_PACKAGE_PREFIX}::Widgets
    ${QT_PACKAGE_PREFIX}::Svg
    ${QT_PACKAGE_PREFIX}::Xml
    QFluent
    simpleRPA_core
)

if(WIN32)
    target_link_libraries(simpleRPA-gui PRIVATE user32 gdi32 ntdll ws2_32 crypt32 schannel dwmapi)
endif()
