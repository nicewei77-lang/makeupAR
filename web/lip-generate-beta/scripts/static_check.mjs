#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import process from 'node:process';

const root = process.cwd();
const required = [
  'src/main.tsx',
  'src/App.tsx',
  'src/localServerClient.ts',
  'src/styles.css',
];
let failed = false;

for (const file of required) {
  if (!fs.existsSync(path.join(root, file))) {
    console.error(`[lip-generate-beta] missing ${file}`);
    failed = true;
  }
}

const app = fs.readFileSync(path.join(root, 'src/App.tsx'), 'utf8');
for (const token of ['Vision', 'MediaPipe', 'Blendshape Assist', '4-Way']) {
  if (!app.includes(token)) {
    console.error(`[lip-generate-beta] App.tsx missing UI token: ${token}`);
    failed = true;
  }
}

if (failed) {
  process.exit(1);
}

console.log('[lip-generate-beta] static check ok');
