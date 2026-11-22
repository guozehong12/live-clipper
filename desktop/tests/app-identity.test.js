const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");
const identity = require("../app-identity");

test("desktop home stays off the official Venus directories", () => {
  const appData = path.join(os.tmpdir(), "Application Support");
  const official = path.join(appData, "Venus");
  const runtime = path.join(appData, "Venus-electron-runtime");
  assert.equal(identity.desktopAppHome("", appData), path.join(appData, "VenusTest"));
  assert.equal(identity.desktopAppHome(official, appData), path.join(appData, "VenusTest"));
  assert.equal(identity.desktopAppHome(runtime, appData), path.join(appData, "VenusTest"));
  const custom = path.join(os.tmpdir(), "venus-test-home");
  assert.equal(identity.desktopAppHome(custom, appData), custom);
  assert.equal(identity.productName, "VenusTest");
  assert.notEqual(identity.productName, identity.officialProductName);
  assert.notEqual(identity.bundleId, identity.officialBundleId);
  assert.equal(identity.updatesEnabled, false);
  const builder = fs.readFileSync(path.join(__dirname, "../electron-builder.yml"), "utf8");
  assert.match(builder, /^appId: com\.guozehong12\.venustest$/m);
  assert.match(builder, /^productName: VenusTest$/m);
  assert.match(builder, /^ {2}identity: null$/m);
  assert.match(builder, /^ {2}notarize: false$/m);
  assert.doesNotMatch(builder, /xattr|com\.apple\.quarantine|spctl --master-disable/);
});
