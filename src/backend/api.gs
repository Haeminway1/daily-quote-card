function getAppBootstrap() {
  return {
    ok: true,
    version: APP_VERSION,
    generatedAt: new Date().toISOString()
  };
}

function withSpreadsheetWriteLock_(writeFn) {
  const lock = LockService.getScriptLock();
  if (!lock.tryLock(8000)) {
    throw new Error('Could not acquire write lock.');
  }
  try {
    const result = writeFn();
    SpreadsheetApp.flush();
    return result;
  } finally {
    lock.releaseLock();
  }
}
