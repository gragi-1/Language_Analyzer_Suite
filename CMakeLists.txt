cmake_minimum_required(VERSION 4.0)
project(PDL C)

set(CMAKE_C_STANDARD 11)

include_directories(.)

add_executable(PDL
        main.c
        utils.h)
