cmake_minimum_required(VERSION 3.16)
project(animeos-reveal LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(Qt6 REQUIRED COMPONENTS Core Gui Quick)

add_executable(reveal main.cpp)
target_link_libraries(reveal PRIVATE Qt6::Core Qt6::Gui Qt6::Quick)
set_target_properties(reveal PROPERTIES
    RUNTIME_OUTPUT_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}")
