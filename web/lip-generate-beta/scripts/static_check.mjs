#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import process from 'node:process';

const root = process.cwd();
const required = [
  'src/main.tsx',
  'src/App.tsx',
  'src/AppWizardShell.tsx',
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
const appWizard = fs.readFileSync(path.join(root, 'src/AppWizardShell.tsx'), 'utf8');
const fullFace = fs.readFileSync(path.join(root, 'src/FullFaceRegionShell.tsx'), 'utf8');
for (const token of [
  'Vision',
  'MediaPipe',
  '표정 보정',
  '입술 마스크 생성',
  '4가지 후보 비교',
]) {
  if (!app.includes(token)) {
    console.error(`[lip-generate-beta] App.tsx missing UI token: ${token}`);
    failed = true;
  }
}

for (const token of [
  'E7 Personalized Generate',
  '얼굴 정렬',
  'Capture',
  '추출',
  '둘 중 하나만 추출',
  '부드럽게',
  'fixture replay 금지',
  'Xcode build pending',
]) {
  if (!appWizard.includes(token)) {
    console.error(`[lip-generate-beta] AppWizardShell.tsx missing UI token: ${token}`);
    failed = true;
  }
}

for (const token of [
  'E7 Full-Face Generate',
  'lip',
  'blush',
  'brow',
  'eyeliner',
  'Runtime payload',
]) {
  if (!fullFace.includes(token)) {
    console.error(`[lip-generate-beta] FullFaceRegionShell.tsx missing UI token: ${token}`);
    failed = true;
  }
}

if (failed) {
  process.exit(1);
}

console.log('[lip-generate-beta] static check ok');
