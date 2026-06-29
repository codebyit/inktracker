#!/usr/bin/env node
/**
 * Sync (or verify) package.json "version" against the canonical VERSION file.
 *
 *   node scripts/sync-version.mjs          # write VERSION -> package.json
 *   node scripts/sync-version.mjs --check   # exit 1 if they differ (CI guard)
 *
 * VERSION is the single source of truth (see VERSIONING.md). The app reads VERSION
 * at runtime; package.json is kept in sync only so npm tooling reports the same number.
 */
import { readFileSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const versionPath = join(root, "VERSION");
const pkgPath = join(root, "package.json");

const check = process.argv.includes("--check");

const version = readFileSync(versionPath, "utf8").trim();
if (!/^\d+\.\d+\.\d+(?:[-+].+)?$/.test(version)) {
  console.error(`VERSION file has an invalid SemVer value: "${version}"`);
  process.exit(1);
}

const pkgRaw = readFileSync(pkgPath, "utf8");
const pkg = JSON.parse(pkgRaw);

if (check) {
  if (pkg.version !== version) {
    console.error(
      `Version mismatch: VERSION=${version} but package.json=${pkg.version}.\n` +
        `Run \`npm run version:sync\` and commit the result.`,
    );
    process.exit(1);
  }
  console.log(`OK: VERSION and package.json both at ${version}`);
  process.exit(0);
}

if (pkg.version === version) {
  console.log(`package.json already at ${version}; nothing to do.`);
  process.exit(0);
}

const updated = pkgRaw.replace(
  /("version"\s*:\s*")[^"]*(")/,
  `$1${version}$2`,
);
if (updated === pkgRaw) {
  console.error('Could not find a "version" field to update in package.json');
  process.exit(1);
}
writeFileSync(pkgPath, updated);
console.log(`Updated package.json version -> ${version}`);
