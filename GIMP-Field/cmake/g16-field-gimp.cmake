# AmmoOS Image — g16 field overlay (field_opt; RTX gated at runtime)
set(AMMOOS_IMAGE_OVERLAY ON CACHE BOOL "Build AmmoOS Image with field tech overlay")
set(AMMOOS_IMAGE_MANDATE "G16_FIELD_SAFETY_MANDATE_v1" CACHE STRING "Field safety mandate id")
set(AMMOOS_OS_BRAND "AmmoOS" CACHE STRING "OS brand")
set(AMMOOS_IMAGE_VERSION "1.0.0" CACHE STRING "AmmoOS Image version")

if(AMMOOS_IMAGE_OVERLAY)
  add_compile_definitions(
    FIELD_AMMOOS_OVERLAY=1
    FIELD_AMMOOS_MANDATE="${AMMOOS_IMAGE_MANDATE}"
    FIELD_AMMOOS_OS=1
    FIELD_AMMOOS_G16_OPT=1
    FIELD_AMMOOS_NO_CLIENT_BROWSER=1
    FIELD_AMMOOS_QUEEN_GATES=1
    FIELD_AMMOOS_VERSION="${AMMOOS_IMAGE_VERSION}"
  )
  if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
    add_compile_options(
      -O3 -march=native -ftree-vectorize -funroll-loops -fomit-frame-pointer
    )
  endif()
  message(STATUS "AmmoOS Image overlay: ${AMMOOS_IMAGE_MANDATE} v${AMMOOS_IMAGE_VERSION}")
endif()