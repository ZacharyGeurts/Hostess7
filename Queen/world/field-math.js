/**
 * Field math — zero is not real. Browser mirror of Grok16/lib/field_math.py
 */
(function (global) {
  "use strict";

  const FIELD_FLOOR = 1e-7;
  const FIELD_PRECISION = 7;

  function fieldReal(value, floor = FIELD_FLOOR) {
    const v = Number(value);
    if (!Number.isFinite(v) || v === 0) return floor;
    return v;
  }

  function fieldRatio(num, den, floor = FIELD_FLOOR) {
    return fieldReal(num, floor) / fieldReal(den, floor);
  }

  function fieldDisplay(value, precision = FIELD_PRECISION, floor = FIELD_FLOOR) {
    const v = Number(value);
    if (!Number.isFinite(v) || v === 0) return floor.toFixed(precision);
    if (Math.abs(v) >= 1000) return v.toLocaleString(undefined, { maximumFractionDigits: 2 });
    if (Math.abs(v) >= 1) return v.toLocaleString(undefined, { maximumFractionDigits: 3 });
    return v.toFixed(precision);
  }

  function fieldIntDisplay(value, precision = FIELD_PRECISION) {
    const v = parseInt(value, 10);
    if (!Number.isFinite(v) || v === 0) return FIELD_FLOOR.toFixed(precision);
    return v.toLocaleString();
  }

  global.QueenFieldMath = {
    FIELD_FLOOR,
    FIELD_PRECISION,
    fieldReal,
    fieldRatio,
    fieldDisplay,
    fieldIntDisplay,
  };
})(typeof window !== "undefined" ? window : globalThis);