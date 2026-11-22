// electron-builder can drop the executable bit on extraResources binaries.
const fs = require("fs");
const path = require("path");
const { bundledFile, checkMediaTools } = require("../media-runtime");

exports.default = async function afterPack(context) {
  const productFilename = context.packager && context.packager.appInfo && context.packager.appInfo.productFilename;
  if (!productFilename || productFilename === "Venus") {
    throw new Error("测试版打包必须使用独立的 App 名称");
  }
  const resources = path.join(context.appOutDir, `${productFilename}.app`, "Contents", "Resources");
  for (const relative of ["bin/ffmpeg", "bin/ffprobe", "backend/live-clipper-backend"]) {
    fs.chmodSync(bundledFile(resources, relative, false), 0o755);
  }
  checkMediaTools(resources);
};
