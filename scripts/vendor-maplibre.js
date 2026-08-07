#!/usr/bin/env node
// maplibre-gl の npm package からビルド済みdistだけを static/ 配下へコピーする。
// バージョン更新時は package.json の maplibre-gl を上げて `npm install` した後にこのスクリプトを再実行する。

const fs = require("fs");
const path = require("path");

const repoRoot = path.resolve(__dirname, "..");
const srcDist = path.join(repoRoot, "node_modules", "maplibre-gl", "dist");
const jsOut = path.join(repoRoot, "project_tabisync", "static", "js", "vendor", "maplibre-gl");
const cssOut = path.join(repoRoot, "project_tabisync", "static", "css", "vendor", "maplibre-gl");

const files = [
  { from: "maplibre-gl.mjs", to: jsOut },
  // maplibre-gl.mjs / maplibre-gl-worker.mjs はどちらもこの共有chunkを
  // 相対URLで読み込むため、片方だけを配布すると実行時404になる。
  { from: "maplibre-gl-shared.mjs", to: jsOut },
  { from: "maplibre-gl-worker.mjs", to: jsOut },
  { from: "maplibre-gl.css", to: cssOut },
];

fs.mkdirSync(jsOut, { recursive: true });
fs.mkdirSync(cssOut, { recursive: true });

for (const { from, to } of files) {
  const src = path.join(srcDist, from);
  const dest = path.join(to, from);
  fs.copyFileSync(src, dest);
  console.log(`copied ${from} -> ${path.relative(repoRoot, dest)}`);
}
