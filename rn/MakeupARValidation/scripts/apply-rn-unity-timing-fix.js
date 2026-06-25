#!/usr/bin/env node

const fs = require('fs');
const path = require('path');

const projectRoot = path.resolve(__dirname, '..');
const targetPath = path.join(
  projectRoot,
  'node_modules',
  '@azesmway',
  'react-native-unity',
  'ios',
  'RNUnityView.mm',
);

const helperBlock = `
- (BOOL)hasValidUnityHostSurface {
    return self.window != nil && self.bounds.size.width > 0 && self.bounds.size.height > 0;
}

- (void)attachUnityRootViewIfReady {
    if (![self unityIsInitialized] || self.bounds.size.width <= 0 || self.bounds.size.height <= 0) {
        return;
    }

    UIView *rootView = self.ufw.appController.rootView;
    rootView.frame = self.bounds;

    if (rootView.superview != self) {
        [rootView removeFromSuperview];
        [self addSubview:rootView];
    }

    [rootView setNeedsLayout];
}

- (void)startUnityIfReady {
    if (![self unityIsInitialized]) {
        if (![self hasValidUnityHostSurface]) {
            NSLog(@"[RNUnityView] Waiting for window/non-zero bounds before Unity init. window=%@ bounds=%@", self.window, NSStringFromCGRect(self.bounds));
            return;
        }

        NSLog(@"[RNUnityView] Initializing Unity with bounds=%@", NSStringFromCGRect(self.bounds));
        [self initUnityModule];
    }

    [self attachUnityRootViewIfReady];
}
`;

const windowLifecycleBlock = `- (void)didMoveToWindow {
   [super didMoveToWindow];
   [self startUnityIfReady];
}

- (void)layoutSubviews {
   [super layoutSubviews];
   [self startUnityIfReady];
}

`;

const legacyInitBlock = `-(id)initWithFrame:(CGRect)frame {
    self = [super initWithFrame:frame];

    if (self) {
        [self startUnityIfReady];
    }

    return self;
}

`;

function fail(message) {
  console.error(`[rn-unity-timing-fix] ${message}`);
  process.exit(1);
}

function replaceBetween(source, startNeedle, endNeedle, replacement) {
  const start = source.indexOf(startNeedle);
  if (start === -1) {
    fail(`Could not find ${startNeedle}`);
  }

  const end = source.indexOf(endNeedle, start);
  if (end === -1) {
    fail(`Could not find ${endNeedle} after ${startNeedle}`);
  }

  return source.slice(0, start) + replacement + source.slice(end);
}

if (!fs.existsSync(targetPath)) {
  fail(`Missing target file: ${targetPath}`);
}

let source = fs.readFileSync(targetPath, 'utf8');
let patched = source;

if (!patched.includes('- (BOOL)hasValidUnityHostSurface')) {
  const unityInitializedBlock = `- (bool)unityIsInitialized {
    return [self ufw] && [[self ufw] appController];
}
`;

  if (!patched.includes(unityInitializedBlock)) {
    fail('Could not find unityIsInitialized block');
  }

  patched = patched.replace(unityInitializedBlock, unityInitializedBlock + helperBlock);
}

const apiRegistration = '[NSClassFromString(@"FrameworkLibAPI") registerAPIforNativeCalls:self];';
const apiRegistrationWithAttach = `${apiRegistration}\n        [self attachUnityRootViewIfReady];`;
if (!patched.includes(apiRegistrationWithAttach)) {
  if (!patched.includes(apiRegistration)) {
    fail('Could not find FrameworkLibAPI registration line');
  }

  patched = patched.replace(
    apiRegistration,
    apiRegistrationWithAttach,
  );
}

patched = replaceBetween(
  patched,
  '- (void)didMoveToWindow',
  '- (void)pauseUnity:',
  windowLifecycleBlock,
);

const legacyBranchStart = patched.indexOf('#else\n\n-(id)initWithFrame:');
if (legacyBranchStart !== -1) {
  const initStart = patched.indexOf('-(id)initWithFrame:', legacyBranchStart);
  const initEnd = patched.indexOf('#endif', initStart);
  if (initEnd === -1) {
    fail('Could not find #endif after legacy initWithFrame');
  }
  patched = patched.slice(0, initStart) + legacyInitBlock + patched.slice(initEnd);
}

const requiredMarkers = [
  '- (BOOL)hasValidUnityHostSurface',
  '- (void)startUnityIfReady',
  '- (void)didMoveToWindow',
  '- (void)layoutSubviews',
  '[self attachUnityRootViewIfReady];',
  '[self startUnityIfReady];',
];

for (const marker of requiredMarkers) {
  if (!patched.includes(marker)) {
    fail(`Patch marker missing after transform: ${marker}`);
  }
}

if (patched !== source) {
  fs.writeFileSync(targetPath, patched);
  console.log(`[rn-unity-timing-fix] Patched ${path.relative(projectRoot, targetPath)}`);
} else {
  console.log('[rn-unity-timing-fix] RNUnityView.mm already patched');
}
