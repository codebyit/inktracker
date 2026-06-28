#!/usr/bin/env node
/**
 * Prepare a release (see VERSIONING.md, hybrid release step 2).
 *
 *   node scripts/prepare-release.mjs <version> [date]
 *
 * 1. Validates <version> is SemVer and strictly greater than the current VERSION.
 * 2. Writes <version> to VERSION and syncs package.json.
 * 3. Updates CHANGELOG.md: promotes a top "## [Unreleased]" section to the new
 *    version (newest-first), or inserts a new "## [<version>] — <date>" section at
 *    the top, leaving any historical sections untouched.
 *
 * Public fork note: each release entry should carry a traceability footer
 *   "Ported from internal vX.Y.Z (commit <sha>)"
 * for changes ported from the internal repo. This script does not add it
 * automatically — add it when writing the entry.
 *
 * It does NOT commit, tag, or push.
 */
import { readFileSync, writeFileSync, existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { execFileSync } from "node:child_process";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const version = (process.argv[2] || "").trim().replace(/^v/, "");
const date = (process.argv[3] || new Date().toISOString().slice(0, 10)).trim();

const SEMVER = /^\d+\.\d+\.\d+(?:[-+].+)?$/;
if (!SEMVER.test(version)) {
  console.error(`Usage: prepare-release.mjs <semver> [date]\nInvalid version: "${version}"`);
  process.exit(1);
}

const versionPath = join(root, "VERSION");
const current = readFileSync(versionPath, "utf8").trim();

function tuple(v) {
  return v.split(/[-+]/)[0].split(".").map(Number);
}
const [a, b, c] = tuple(version);
const [x, y, z] = tuple(current);
const greater = a > x || (a === x && (b > y || (b === y && c > z)));
if (!greater && version !== current) {
  console.error(`New version ${version} must be greater than current ${current}.`);
  process.exit(1);
}

writeFileSync(versionPath, `${version}\n`);
execFileSync(process.execPath, [join(root, "scripts", "sync-version.mjs")], {
  stdio: "inherit",
});

const clPath = join(root, "CHANGELOG.md");
if (!existsSync(clPath)) {
  console.warn("CHANGELOG.md not found — skipping changelog update.");
  process.exit(0);
}
let cl = readFileSync(clPath, "utf8");
const heading = `## [${version}] — ${date}`;
const escaped = version.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

if (new RegExp(`^##\\s*\\[?${escaped}\\]?`, "im").test(cl)) {
  console.log(`CHANGELOG already has an entry for ${version}; leaving it as-is.`);
} else {
  const firstVer = cl.search(/^##\s*\[\d+\.\d+\.\d+\]/m);
  if (firstVer === -1) {
    const stub = `${heading}\n\n_Release ${version}._\n`;
    cl = /^---\s*$/m.test(cl)
      ? cl.replace(/^---\s*$/m, `---\n\n${stub}`)
      : `${stub}\n${cl}`;
    console.warn(`Inserted a CHANGELOG stub for ${version} — edit it before releasing.`);
  } else {
    const head = cl.slice(0, firstVer);
    const rest = cl.slice(firstVer);
    if (/^##\s*\[?Unreleased\]?/im.test(head)) {
      cl =
        head.replace(/^##\s*\[?Unreleased\]?.*$/im, `## [Unreleased]\n\n${heading}`) +
        rest;
      console.log(`Promoted top Unreleased section to ${version}.`);
    } else {
      cl = `${head}${heading}\n\n_Release ${version}._\n\n${rest}`;
      console.warn(`Inserted a CHANGELOG stub for ${version} — edit it before releasing.`);
    }
  }
}
writeFileSync(clPath, cl);
console.log(`Prepared release ${version} (${date}).`);
