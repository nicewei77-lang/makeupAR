# M0 Environment Status

Date: 2026-06-19
Workspace: `/Users/wiseungcheol/Desktop/makeupAR`

## Verdict

Red.

The non-Xcode tooling is mostly ready, including Node 22, Watchman, CocoaPods,
Unity Hub, Unity 6.3 LTS, and Unity iOS Build Support. The environment is not
ready for Session 2 until macOS is upgraded and full Xcode 26.0+ is installed,
selected, and first-launched.

## Verified Commands

| Check | Result | Status |
| --- | --- | --- |
| `sw_vers` | macOS 14.3.1, build 23D60 | Blocker for Xcode 26+ |
| `xcodebuild -version` | Fails: active developer directory is Command Line Tools | Blocked |
| `xcode-select -p` | `/Library/Developer/CommandLineTools` | Blocked |
| `node -v` | `v22.23.0` | Ready |
| `npm -v` | `10.9.8` | Ready |
| `watchman --version` | `2026.06.15.00` | Ready |
| `pod --version` | `1.16.2` | Ready |

Note: this Codex runner forces `LC_ALL=C`, so plain `pod --version` prints a
UTF-8 warning before `1.16.2`. UTF-8 exports were added to `~/.zshrc` and
`~/.zprofile`; with `LANG=en_US.UTF-8 LC_ALL=en_US.UTF-8`, `pod --version`
prints cleanly.

## Installed During M0

- Homebrew `node@22` installed and linked as the active `node`/`npm`.
- Homebrew `watchman` installed.
- Homebrew `cocoapods` installed.
- Unity Hub `3.18.3` installed at `/Applications/Unity Hub.app`.
- Unity Editor `6000.3.18f1` ARM64 installed at:
  `/Applications/Unity/Hub/Editor/6000.3.18f1/Unity.app`
- Unity iOS Build Support installed at:
  `/Applications/Unity/Hub/Editor/6000.3.18f1/PlaybackEngines/iOSSupport`

## Xcode Status

No `/Applications/Xcode.app` is installed.

Apple's current App Store Xcode listing is Xcode 26.x and requires macOS 26.2 or
later. This Mac is on macOS 14.3.1, so Xcode 26.0+ cannot be installed and
activated on the current OS state.

Required next Xcode steps:

1. Upgrade macOS to a version supported by Xcode 26.0+.
2. Install full Xcode 26.0+ at `/Applications/Xcode.app`.
3. Run `sudo xcode-select -s /Applications/Xcode.app/Contents/Developer`.
4. Complete first launch / license setup.
5. Re-check `xcodebuild -version` and `xcode-select -p`.

## iPhone Status

No iPhone is currently visible over USB in `system_profiler SPUSBDataType`.
Because full Xcode is missing, `xcrun xctrace list devices` is also unavailable.

Required device-side steps after Xcode is installed:

1. Connect an iPhone 11 or newer by USB.
2. Unlock the iPhone and tap Trust This Computer.
3. Enable Developer Mode on the iPhone if prompted.
4. Open Xcode Device Hub / Devices and Simulators.
5. Confirm the iPhone appears as a run destination.

## Sources Checked

- Apple App Store Xcode listing: https://apps.apple.com/us/app/xcode/id497799835
- Unity 6 release page: https://unity.com/releases/unity-6
- Unity AR Foundation 6.3 docs: https://docs.unity3d.com/Packages/com.unity.xr.arfoundation@6.3/manual/project-setup/install-arfoundation.html
- Unity Apple ARKit XR Plug-in 6.3 docs: https://docs.unity3d.com/Packages/com.unity.xr.arkit@6.3/manual/index.html
