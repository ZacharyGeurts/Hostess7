# Delegates to Grok16 canonical mandate.
if(DEFINED ENV{GROK16_ROOT} AND NOT "$ENV{GROK16_ROOT}" STREQUAL "")
  set(_GROK16_ROOT "$ENV{GROK16_ROOT}")
else()
  get_filename_component(_GROK16_ROOT "${CMAKE_CURRENT_LIST_DIR}/../../../Grok16" ABSOLUTE)
endif()
include("${_GROK16_ROOT}/cmake/g16-field-mandate.cmake")
unset(_GROK16_ROOT)