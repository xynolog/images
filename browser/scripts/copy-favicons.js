#!/usr/bin/env node
/**
 * Stage the brand submodule's favicons/ whole into public/favicons/, where
 * index.html links them. brand/ sits beside browser/, in the repository and in
 * the build container (scripts/browser-container.sh).
 */

const fs = require('fs');
const path = require('path');

const sourceDir = path.join(__dirname, '../../brand/favicons');
const targetDir = path.join(__dirname, '../public/favicons');

if (!fs.existsSync(sourceDir)) {
  console.error(`copy-favicons: ${sourceDir} does not exist; check out the brand submodule`);
  process.exit(1);
}
fs.rmSync(targetDir, { recursive: true, force: true });
fs.cpSync(sourceDir, targetDir, { recursive: true });

const copied = fs.readdirSync(targetDir).length;
if (copied === 0) {
  console.error('copy-favicons: nothing copied from', sourceDir);
  process.exit(1);
}
console.log(`✅ favicons staged (${copied} files)`);
