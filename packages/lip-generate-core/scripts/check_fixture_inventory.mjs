#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import process from 'node:process';

const repoRoot = path.resolve(import.meta.dirname, '../../..');
const inventoryPath = path.join(
  repoRoot,
  'fixtures/lip-generate/fixture_inventory.json',
);

function fail(message) {
  console.error(`[lip-generate-core] ${message}`);
  process.exitCode = 1;
}

function readJson(filePath) {
  return JSON.parse(fs.readFileSync(filePath, 'utf8'));
}

function assertRepoPathExists(label, repoRelativePath) {
  if (!repoRelativePath || path.isAbsolute(repoRelativePath)) {
    fail(`${label} must be a repo-relative path: ${repoRelativePath}`);
    return;
  }
  const absolutePath = path.join(repoRoot, repoRelativePath);
  if (!fs.existsSync(absolutePath)) {
    fail(`${label} does not exist: ${repoRelativePath}`);
  }
}

if (!fs.existsSync(inventoryPath)) {
  fail(`missing fixture inventory: ${inventoryPath}`);
} else {
  const inventory = readJson(inventoryPath);
  if (inventory.schemaVersion !== 'e7-lip-generate-fixture-inventory-v0') {
    fail('unsupported fixture inventory schemaVersion');
  }
  if (!Array.isArray(inventory.fixtures) || inventory.fixtures.length === 0) {
    fail('fixture inventory must contain at least one fixture');
  }
  const ids = new Set();
  for (const fixture of inventory.fixtures ?? []) {
    if (!fixture.fixtureId) {
      fail('fixture is missing fixtureId');
      continue;
    }
    if (ids.has(fixture.fixtureId)) {
      fail(`duplicate fixtureId: ${fixture.fixtureId}`);
    }
    ids.add(fixture.fixtureId);
    if (fixture.privacy?.localOnly !== true) {
      fail(`${fixture.fixtureId} privacy.localOnly must be true`);
    }
    if (fixture.privacy?.offDeviceUpload !== false) {
      fail(`${fixture.fixtureId} privacy.offDeviceUpload must be false`);
    }
    if (fixture.privacy?.longTermRawFrameStored !== false) {
      fail(`${fixture.fixtureId} privacy.longTermRawFrameStored must be false`);
    }
    for (const [label, key] of [
      ['framePath', 'framePath'],
      ['arFaceExportPath', 'arFaceExportPath'],
      ['fusionSummaryPath', 'fusionSummaryPath'],
      ['referenceMaskPath', 'referenceMaskPath'],
    ]) {
      assertRepoPathExists(`${fixture.fixtureId}.${label}`, fixture[key]);
    }
    for (const provider of ['vision', 'mediapipe']) {
      const providerEntry = fixture.providers?.[provider];
      if (!providerEntry) {
        fail(`${fixture.fixtureId} missing provider entry: ${provider}`);
        continue;
      }
      for (const key of ['contourPath', 'maskPath', 'pointsPath']) {
        if (providerEntry[key]) {
          assertRepoPathExists(
            `${fixture.fixtureId}.${provider}.${key}`,
            providerEntry[key],
          );
        }
      }
    }
  }
  if (!ids.has(inventory.defaultFixtureId)) {
    fail(`defaultFixtureId not found: ${inventory.defaultFixtureId}`);
  }
}

if (process.exitCode) {
  process.exit(process.exitCode);
}

console.log('[lip-generate-core] fixture inventory ok');
