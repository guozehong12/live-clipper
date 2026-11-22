const path = require("path");

const identity = {
  productName: "VenusTest",
  bundleId: "com.guozehong12.venustest",
  dataDirName: "VenusTest",
  officialProductName: "Venus",
  officialBundleId: "com.dingshuxin.venus",
  officialDataDirName: "Venus",
  updaterCacheDirName: "venustest-desktop-updater",
  updatesEnabled: false,
};

function isOfficialDataDirectory(candidate) {
  if (typeof candidate !== "string" || !candidate.trim()) return false;
  const base = path.basename(path.resolve(candidate));
  return base === identity.officialDataDirName || base === `${identity.officialDataDirName}-electron-runtime`;
}

function desktopAppHome(configuredHome, appDataDir) {
  const configured = String(configuredHome || "").trim();
  const isolated = path.join(appDataDir, identity.dataDirName);
  if (configured && path.isAbsolute(configured) && !isOfficialDataDirectory(configured)) return configured;
  return isolated;
}

module.exports = { ...identity, isOfficialDataDirectory, desktopAppHome };
