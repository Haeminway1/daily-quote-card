// Shared GAS-compatible exponential backoff helper. Keep in sync with
// library/backend/gas-backoff.js when changing retry behavior.
(function attachGasBackoff(root, factory) {
  const api = factory(root);
  root.GasBackoff = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function buildGasBackoff(root) {
  const TRANSIENT_STATUS = [408, 429, 500, 502, 503, 504];

  function isTransientError(error) {
    const status = Number(error && (error.status || error.statusCode || error.code));
    if (TRANSIENT_STATUS.indexOf(status) !== -1) return true;
    const message = String((error && error.message) || error || '').toLowerCase();
    return /timeout|timed out|too many|rate limit|temporar|quota|backend error|service unavailable/.test(message);
  }

  function backoffDelayMs(attemptIndex, options) {
    const base = Math.max(0, Number(options.baseDelayMs == null ? 250 : options.baseDelayMs));
    const max = Math.max(base, Number(options.maxDelayMs == null ? 8000 : options.maxDelayMs));
    const raw = Math.min(max, base * Math.pow(2, Math.max(0, attemptIndex - 1)));
    const jitterRatio = Math.max(0, Number(options.jitterRatio == null ? 0.25 : options.jitterRatio));
    if (!jitterRatio) return raw;
    const spread = raw * jitterRatio;
    return Math.round(raw - spread + Math.random() * spread * 2);
  }

  function withBackoff(fn, options) {
    const opts = options || {};
    const maxAttempts = Math.max(1, Number(opts.maxAttempts == null ? 5 : opts.maxAttempts));
    let attempt = 0;
    while (attempt < maxAttempts) {
      attempt += 1;
      try {
        return fn(attempt);
      } catch (error) {
        if (attempt >= maxAttempts || !isTransientError(error)) throw error;
        Utilities.sleep(backoffDelayMs(attempt, opts));
      }
    }
    throw new Error('withBackoff exhausted attempts.');
  }

  return {
    backoffDelayMs: backoffDelayMs,
    isTransientError: isTransientError,
    withBackoff: withBackoff
  };
});
