# M1 Standalone AR Runbook

Use this only after full Xcode is installed and an iPhone 11 or newer is connected, trusted, and visible as a run destination.

## Unity Setup

1. Open `/Users/wiseungcheol/Desktop/makeupAR/unity/MakeupARUnityValidation` in Unity `6000.3.18f1`.
2. Let Package Manager resolve:
   - `com.unity.xr.arfoundation` `6.3.5`
   - `com.unity.xr.arkit` `6.3.5`
   - `com.unity.xr.management` `4.5.4`
3. Run menu item `Makeup AR Validation > Configure Project And Scene`.
4. Confirm the generated scene contains:
   - `AR Session`
   - `XR Origin`
   - `AR Camera`
   - `AR Camera Manager`
   - `AR Face Manager`
   - `Face Tracking Status Reporter`
5. Confirm `Project Settings > XR Plug-in Management > iOS > ARKit` is enabled.
6. Confirm `Project Settings > Player > iOS > Camera Usage Description` is set.

## Export

Run menu item `Makeup AR Validation > Export iOS Project`.

Expected export path:

```txt
/Users/wiseungcheol/Desktop/makeupAR/unity-builds/ios-export
```

## Xcode Run

1. Open the exported Xcode project.
2. Select the connected iPhone as the destination.
3. Configure signing if Xcode requires it.
4. Build and run on the iPhone.
5. Accept camera permission.
6. Use the front camera on a face and capture:
   - Xcode build result
   - Runtime log lines starting with `[M1]`
   - Screenshot or screen recording of the face overlay if possible

Required success log shape:

```txt
[M1] AR support state: ...
[M1] ... Current tracked face count: 1; Face detected: true
```
