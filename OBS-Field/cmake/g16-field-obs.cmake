# Field OBS — g16 AmmoOS overlay (field_opt; RTX gated at runtime)
set(FIELD_OBS_OVERLAY ON CACHE BOOL "Build Field OBS with AmmoOS g16 overlay")
set(FIELD_OBS_MANDATE "G16_FIELD_SAFETY_MANDATE_v1" CACHE STRING "Field safety mandate id")
set(FIELD_OBS_BRAND "Field OBS" CACHE STRING "Field OBS product brand")
set(FIELD_OBS_VERSION "1.0.0" CACHE STRING "Field OBS version")
set(FIELD_OBS_G16_PROFILE "field_opt" CACHE STRING "Grok16 field profile for OBS build")

if(FIELD_OBS_OVERLAY)
  add_compile_definitions(
    FIELD_AMMOOS_OVERLAY=1
    FIELD_AMMOOS_MANDATE="${FIELD_OBS_MANDATE}"
    FIELD_AMMOOS_OS=1
    FIELD_AMMOOS_G16_OPT=1
    FIELD_AMMOOS_NO_CLIENT_BROWSER=1
    FIELD_AMMOOS_QUEEN_GATES=1
    FIELD_OBS_FIELD=1
    FIELD_OBS_G16=1
    FIELD_OBS_VERSION="${FIELD_OBS_VERSION}"
    FIELD_OBS_BRAND="${FIELD_OBS_BRAND}"
  )
  if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
    add_compile_options(
      -O3 -march=native -ftree-vectorize -funroll-loops -fomit-frame-pointer
    )
  endif()
  message(STATUS "Field OBS g16 overlay: ${FIELD_OBS_MANDATE} v${FIELD_OBS_VERSION} profile=${FIELD_OBS_G16_PROFILE}")
endif()