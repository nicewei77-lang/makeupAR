using System.Reflection;
using UnityEngine;
using UnityEngine.XR.ARFoundation;
using UnityEngine.XR.ARSubsystems;
using UnityEngine.XR.Management;

public sealed class FaceTrackingStatusReporter : MonoBehaviour
{
    [SerializeField] private ARSession arSession;
    [SerializeField] private ARCameraManager cameraManager;
    [SerializeField] private ARFaceManager faceManager;
    [SerializeField] private float logIntervalSeconds = 1.0f;
    [SerializeField] private bool drawDebugOverlay = true;

    private int lastFaceCount = -1;
    private string faceSupportState = "Unknown";
    private float nextLogTime;

    private void OnEnable()
    {
        ARSession.stateChanged += OnArSessionStateChanged;
    }

    private void OnDisable()
    {
        ARSession.stateChanged -= OnArSessionStateChanged;
    }

    private void Awake()
    {
        if (arSession == null)
        {
            arSession = FindFirstObjectByType<ARSession>();
        }

        if (cameraManager == null)
        {
            cameraManager = FindFirstObjectByType<ARCameraManager>();
        }

        if (faceManager == null)
        {
            faceManager = FindFirstObjectByType<ARFaceManager>();
        }

        RefreshFaceSupportState();
        LogStatus(true);
    }

    private void Update()
    {
        int faceCount = CountTrackedFaces();
        bool faceCountChanged = faceCount != lastFaceCount;

        if (faceCountChanged || Time.unscaledTime >= nextLogTime)
        {
            LogStatus(false);
        }
    }

    private void OnGUI()
    {
        if (!drawDebugOverlay)
        {
            return;
        }

        int faceCount = CountTrackedFaces();
        bool faceDetected = faceCount > 0;

        GUI.color = Color.white;
        GUILayout.BeginArea(new Rect(24, 24, 720, 220), GUI.skin.box);
        GUILayout.Label("Makeup AR Unity M1 Validation");
        GUILayout.Label("AR support state: " + ARSession.state);
        GUILayout.Label(GetCameraDirectionStatus());
        GUILayout.Label("Face tracking support state: " + faceSupportState);
        GUILayout.Label("Tracked face count: " + faceCount);
        GUILayout.Label("Face detected: " + faceDetected.ToString().ToLowerInvariant());
        GUILayout.EndArea();
    }

    private int CountTrackedFaces()
    {
        if (faceManager == null)
        {
            return 0;
        }

        int count = 0;
        foreach (ARFace _ in faceManager.trackables)
        {
            count++;
        }

        return count;
    }

    private void LogStatus(bool force)
    {
        RefreshFaceSupportState();

        int faceCount = CountTrackedFaces();
        bool faceDetected = faceCount > 0;

        if (force || faceCount != lastFaceCount || Time.unscaledTime >= nextLogTime)
        {
            Debug.Log(
                "[M1] AR support state: " + ARSession.state
                + "; " + GetCameraDirectionStatus()
                + "; Face tracking support state: " + faceSupportState
                + "; Current tracked face count: " + faceCount
                + "; Face detected: " + faceDetected.ToString().ToLowerInvariant());

            lastFaceCount = faceCount;
            nextLogTime = Time.unscaledTime + logIntervalSeconds;
        }
    }

    private void OnArSessionStateChanged(ARSessionStateChangedEventArgs args)
    {
        Debug.Log("[M1] AR support state changed: " + args.state);
        LogStatus(true);
    }

    private string GetCameraDirectionStatus()
    {
        if (cameraManager == null)
        {
            return "Camera direction: ARCameraManager not found";
        }

        return "Camera requested/current: "
            + cameraManager.requestedFacingDirection
            + "/"
            + cameraManager.currentFacingDirection;
    }

    private void RefreshFaceSupportState()
    {
        XRFaceSubsystem faceSubsystem = null;
        XRGeneralSettings generalSettings = XRGeneralSettings.Instance;
        XRManagerSettings managerSettings = generalSettings != null ? generalSettings.Manager : null;

        if (managerSettings != null && managerSettings.activeLoader != null)
        {
            faceSubsystem = managerSettings.activeLoader.GetLoadedSubsystem<XRFaceSubsystem>();
        }

        if (faceSubsystem == null)
        {
            faceSupportState = "XRFaceSubsystem not loaded";
            return;
        }

        XRFaceSubsystemDescriptor descriptor = faceSubsystem.subsystemDescriptor;
        faceSupportState = "XRFaceSubsystem loaded"
            + "; running=" + faceSubsystem.running
            + "; supportsFacePose=" + ReadBoolProperty(descriptor, "supportsFacePose")
            + "; supportsFaceMeshVerticesAndIndices=" + ReadBoolProperty(descriptor, "supportsFaceMeshVerticesAndIndices")
            + "; supportsFaceMeshUVs=" + ReadBoolProperty(descriptor, "supportsFaceMeshUVs")
            + "; supportsEyeTracking=" + ReadBoolProperty(descriptor, "supportsEyeTracking");
    }

    private static string ReadBoolProperty(object target, string propertyName)
    {
        if (target == null)
        {
            return "unknown";
        }

        PropertyInfo property = target.GetType().GetProperty(propertyName, BindingFlags.Public | BindingFlags.Instance);
        if (property == null || property.PropertyType != typeof(bool))
        {
            return "unknown";
        }

        return ((bool)property.GetValue(target)).ToString().ToLowerInvariant();
    }
}
