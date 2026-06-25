const fs = require('fs');
const path = require('path');

const unityViewPath = path.join(
  __dirname,
  '..',
  'node_modules',
  '@azesmway',
  'react-native-unity',
  'ios',
  'RNUnityView.mm',
);

const marker = '[MakeupAR][RNUnityView]';

function replaceOnce(source, search, replacement, label) {
  if (!source.includes(search)) {
    throw new Error(`Unable to patch RNUnityView.mm: missing ${label}`);
  }

  return source.replace(search, replacement);
}

if (!fs.existsSync(unityViewPath)) {
  console.log('[MakeupAR] react-native-unity iOS source not found, skipping patch');
  process.exit(0);
}

let source = fs.readFileSync(unityViewPath, 'utf8');

if (source.includes(marker)) {
  console.log('[MakeupAR] react-native-unity iOS patch already applied');
  process.exit(0);
}

source = replaceOnce(
  source,
  `    NSBundle* bundle = [NSBundle bundleWithPath: bundlePath];
    if ([bundle isLoaded] == false) [bundle load];

    UnityFramework* ufw = [bundle.principalClass getInstance];`,
  `    NSBundle* bundle = [NSBundle bundleWithPath: bundlePath];
    NSLog(@"[MakeupAR][RNUnityView] UnityFrameworkLoad path=%@ exists=%d loaded=%d",
          bundlePath,
          [[NSFileManager defaultManager] fileExistsAtPath:bundlePath],
          [bundle isLoaded]);
    if ([bundle isLoaded] == false && ![bundle load]) {
        NSLog(@"[MakeupAR][RNUnityView] UnityFramework load failed path=%@", bundlePath);
        return nil;
    }

    UnityFramework* ufw = [bundle.principalClass getInstance];`,
  'UnityFramework load diagnostics',
);

source = replaceOnce(
  source,
  `- (bool)unityIsInitialized {
    return [self ufw] && [[self ufw] appController];
}

- (void)initUnityModule {`,
  `- (bool)unityIsInitialized {
    return [self ufw] && [[self ufw] appController];
}

- (void)attachUnityRootView:(NSString *)reason {
    if (![self unityIsInitialized]) {
        NSLog(@"[MakeupAR][RNUnityView] attach skipped reason=%@ initialized=0", reason);
        return;
    }

    UIView *rootView = self.ufw.appController.rootView;
    if (rootView == nil) {
        NSLog(@"[MakeupAR][RNUnityView] attach skipped reason=%@ rootView=nil", reason);
        return;
    }

    rootView.frame = self.bounds;
    rootView.autoresizingMask = UIViewAutoresizingFlexibleWidth | UIViewAutoresizingFlexibleHeight;

    if (rootView.superview != self) {
        [rootView removeFromSuperview];
        [self insertSubview:rootView atIndex:0];
    }

    UIWindow *main = [[[UIApplication sharedApplication] delegate] window];
    if (main != nil) {
        [main makeKeyAndVisible];
    }

    NSLog(@"[MakeupAR][RNUnityView] attached reason=%@ bounds=%@ rootBounds=%@",
          reason,
          NSStringFromCGRect(self.bounds),
          NSStringFromCGRect(rootView.bounds));
}

- (void)initUnityModule {`,
  'Unity root view attach helper',
);

source = replaceOnce(
  source,
  `        if([self unityIsInitialized]) {
            return;
        }

        [self setUfw: UnityFrameworkLoad()];
        [[self ufw] registerFrameworkListener: self];`,
  `        if([self unityIsInitialized]) {
            [self attachUnityRootView:@"already-initialized"];
            return;
        }

        [self setUfw: UnityFrameworkLoad()];
        if (![self ufw]) {
            return;
        }
        [[self ufw] registerFrameworkListener: self];`,
  'init guard',
);

source = replaceOnce(
  source,
  `        [[self ufw] runEmbeddedWithArgc: gArgc argv: array appLaunchOpts: appLaunchOpts];
        [[self ufw] appController].quitHandler = ^(){ NSLog(@"AppController.quitHandler called"); };
        [self.ufw.appController.rootView removeFromSuperview];

        if (@available(iOS 13.0, *)) {
            [[[[self ufw] appController] window] setWindowScene: nil];
        } else {
            [[[[self ufw] appController] window] setScreen: nil];
        }

        [[[[self ufw] appController] window] addSubview: self.ufw.appController.rootView];
        [[[[self ufw] appController] window] makeKeyAndVisible];
        [[[[[[self ufw] appController] window] rootViewController] view] setNeedsLayout];

        [NSClassFromString(@"FrameworkLibAPI") registerAPIforNativeCalls:self];`,
  `        NSLog(@"[MakeupAR][RNUnityView] runEmbedded begin argc=%u bounds=%@",
              count,
              NSStringFromCGRect(self.bounds));
        int argc = count > 0 ? (int)count : gArgc;
        [[self ufw] runEmbeddedWithArgc:argc argv:array appLaunchOpts:appLaunchOpts];
        NSLog(@"[MakeupAR][RNUnityView] runEmbedded end initialized=%d appController=%@ rootView=%@",
              [self unityIsInitialized],
              [[self ufw] appController],
              [[self ufw] appController].rootView);
        [[self ufw] appController].quitHandler = ^(){ NSLog(@"AppController.quitHandler called"); };
        [self attachUnityRootView:@"init"];

        [NSClassFromString(@"FrameworkLibAPI") registerAPIforNativeCalls:self];`,
  'runEmbedded and root view attachment',
);

source = replaceOnce(
  source,
  `- (void)layoutSubviews {
   [super layoutSubviews];

   if([self unityIsInitialized]) {
      self.ufw.appController.rootView.frame = self.bounds;
      [self addSubview:self.ufw.appController.rootView];
   }
}

- (void)pauseUnity:(BOOL * _Nonnull)pause {`,
  `- (void)layoutSubviews {
   [super layoutSubviews];

   if(![self unityIsInitialized]) {
      [self initUnityModule];
   }

   [self attachUnityRootView:@"layoutSubviews"];
}

- (void)didMoveToWindow {
    [super didMoveToWindow];

    if (self.window != nil) {
        [self initUnityModule];
        [self attachUnityRootView:@"didMoveToWindow"];
    }
}

- (void)pauseUnity:(BOOL * _Nonnull)pause {`,
  'Fabric layout/didMove initialization',
);

source = replaceOnce(
  source,
  `- (void)postMessage:(NSString *)gameObject methodName:(NSString*)methodName message:(NSString*) message {
    dispatch_async(dispatch_get_main_queue(), ^{
        [[self ufw] sendMessageToGOWithName:[gameObject UTF8String] functionName:[methodName UTF8String] message:[message UTF8String]];
    });
}`,
  `- (void)postMessage:(NSString *)gameObject methodName:(NSString*)methodName message:(NSString*) message {
    dispatch_async(dispatch_get_main_queue(), ^{
        if (![self unityIsInitialized]) {
            [self initUnityModule];
        }
        NSLog(@"[MakeupAR][RNUnityView] postMessage gameObject=%@ method=%@ initialized=%d",
              gameObject,
              methodName,
              [self unityIsInitialized]);
        [[self ufw] sendMessageToGOWithName:[gameObject UTF8String] functionName:[methodName UTF8String] message:[message UTF8String]];
    });
}`,
  'postMessage lazy init',
);

source = replaceOnce(
  source,
  `    self.onUnityMessage = [self](NSDictionary* data) {
      if (_eventEmitter != nil) {
        auto gridViewEventEmitter = std::static_pointer_cast<RNUnityViewEventEmitter const>(_eventEmitter);
        facebook::react::RNUnityViewEventEmitter::OnUnityMessage event = {
          .message=[[data valueForKey:@"message"] UTF8String]
        };
        gridViewEventEmitter->onUnityMessage(event);
      }
    };
  }

  return self;
}`,
  `    self.onUnityMessage = [self](NSDictionary* data) {
      if (_eventEmitter != nil) {
        auto gridViewEventEmitter = std::static_pointer_cast<RNUnityViewEventEmitter const>(_eventEmitter);
        facebook::react::RNUnityViewEventEmitter::OnUnityMessage event = {
          .message=[[data valueForKey:@"message"] UTF8String]
        };
        gridViewEventEmitter->onUnityMessage(event);
      }
    };

    [self initUnityModule];
  }

  return self;
}`,
  'Fabric initWithFrame initialization',
);

fs.writeFileSync(unityViewPath, source);
console.log('[MakeupAR] react-native-unity iOS patch applied');
