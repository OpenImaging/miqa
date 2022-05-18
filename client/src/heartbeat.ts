// eslint-disable-next-line import/prefer-default-export
export const setupHeartbeat = async (
  key: string,
  expirationCallback: () => Promise<void>,
  timeout: number = 10 * 60 * 1000, // 10 minutes
) => {
  // Note that if getItem returns null, this will use the unix epoch, which is fine
  const lastHeartbeat = +new Date(window.localStorage.getItem(key));

  // Check expiration
  if (+new Date() - lastHeartbeat > timeout) {
    localStorage.setItem(key, new Date().toISOString());
    await expirationCallback();
  }

  // Update heartbeat while the tab is open
  setInterval(() => {
    localStorage.setItem(key, new Date().toISOString());
  }, 10_000);
};
