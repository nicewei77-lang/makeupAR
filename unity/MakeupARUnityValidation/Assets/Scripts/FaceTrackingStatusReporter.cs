using System.Text;
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
    [SerializeField] private RNBridge rnBridge;
    [SerializeField] private float logIntervalSeconds = 1.0f;
    [SerializeField] private bool drawDebugOverlay = true;

    private int lastFaceCount = -1;
    private int lastTotalTrackables = -1;
    private int lastSentFaceCount = -1;
    private int lastSentTotalTrackables = -1;
    private string faceSupportState = "Unknown";
    private string lastTrackingStates = string.Empty;
    private string lastSentTrackingStates = string.Empty;
    private float nextLogTime;
    private GUIStyle debugBoxStyle;
    private GUIStyle debugTitleStyle;
    private GUIStyle debugLabelStyle;

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

        if (rnBridge == null)
        {
            rnBridge = FindFirstObjectByType<RNBridge>();
        }

        RefreshFaceSupportState();
        LogStatus(true);
    }

    private void Update()
    {
        int faceCount = CountTrackedFaces(out int totalTrackables, out string trackingStates);
        bool faceCountChanged = faceCount != lastFaceCount
            || totalTrackables != lastTotalTrackables
            || trackingStates != lastTrackingStates;

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

        int faceCount = CountTrackedFaces(out int totalTrackables, out string trackingStates);
        bool faceDetected = faceCount > 0;

        EnsureDebugStyles();

        GUI.color = Color.white;
        GUILayout.BeginArea(new Rect(24, 24, 1060, 420), debugBoxStyle);
        GUILayout.Label("Makeup AR Unity M7", debugTitleStyle);
        GUILayout.Label("AR: " + ARSession.state, debugLabelStyle);
        GUILayout.Label(GetCameraDirectionStatus(), debugLabelStyle);
        GUILayout.Label("Tracked faces: " + faceCount + " / total " + totalTrackables, debugLabelStyle);
        GUILayout.Label("Tracking states: " + trackingStates, debugLabelStyle);
        GUILayout.Label("Face detected: " + faceDetected.ToString().ToLowerInvariant(), debugLabelStyle);
        GUILayout.EndArea();
    }

    private void EnsureDebugStyles()
    {
        if (debugBoxStyle != null)
        {
            return;
        }

        debugBoxStyle = new GUIStyle(GUI.skin.box)
        {
            padding = new RectOffset(24, 24, 20, 20)
        };

        debugTitleStyle = new GUIStyle(GUI.skin.label)
        {
            fontSize = 34,
            fontStyle = FontStyle.Bold,
            wordWrap = true,
            normal = { textColor = Color.white }
        };

        debugLabelStyle = new GUIStyle(GUI.skin.label)
        {
            fontSize = 28,
            wordWrap = true,
            normal = { textColor = Color.white }
        };
    }

    private int CountTrackedFaces(out int totalTrackables, out string trackingStates)
    {
        totalTrackables = 0;

        if (faceManager == null)
        {
            trackingStates = "faceManager:null";
            return 0;
        }

        int count = 0;
        StringBuilder stateBuilder = new StringBuilder();

        foreach (ARFace face in faceManager.trackables)
        {
            if (totalTrackables > 0)
            {
                stateBuilder.Append(",");
            }

            stateBuilder
                .Append(face.trackableId)
                .Append(":")
                .Append(face.trackingState);

            totalTrackables++;

            if (face.trackingState == TrackingState.Tracking)
            {
                count++;
            }
        }

        trackingStates = totalTrackables == 0 ? "none" : stateBuilder.ToString();
        return count;
    }

    private void LogStatus(bool force)
    {
        RefreshFaceSupportState();

        int faceCount = CountTrackedFaces(out int totalTrackables, out string trackingStates);
        bool faceDetected = faceCount > 0;

        if (force
            || faceCount != lastFaceCount
            || totalTrackables != lastTotalTrackables
            || trackingStates != lastTrackingStates
            || Time.unscaledTime >= nextLogTime)
        {
            Debug.Log(
                "[M1] AR support state: " + ARSession.state
                + "; " + GetCameraDirectionStatus()
                + "; Face tracking support state: " + faceSupportState
                + "; Current tracked face count: " + faceCount
                + "; Total face trackables: " + totalTrackables
                + "; Face tracking states: " + trackingStates
                + "; Face detected: " + faceDetected.ToString().ToLowerInvariant());

            lastFaceCount = faceCount;
            lastTotalTrackables = totalTrackables;
            lastTrackingStates = trackingStates;
            nextLogTime = Time.unscaledTime + logIntervalSeconds;
        }

        SendFaceStateToReactNative(faceDetected, faceCount, totalTrackables, trackingStates, force);
    }

    private void OnArSessionStateChanged(ARSessionStateChangedEventArgs args)
    {
        Debug.Log("[M1] AR support state changed: " + args.state);
        LogStatus(true);
    }

    private void SendFaceStateToReactNative(
        bool faceDetected,
        int faceCount,
        int totalTrackables,
        string trackingStates,
        bool force)
    {
        if (!force
            && faceCount == lastSentFaceCount
            && totalTrackables == lastSentTotalTrackables
            && trackingStates == lastSentTrackingStates)
        {
            return;
        }

        if (rnBridge == null)
        {
            rnBridge = FindFirstObjectByType<RNBridge>();
        }

        if (rnBridge == null)
        {
            Debug.LogWarning("[M6] unity_to_rn_face_state_skipped RNBridge not found");
            return;
        }

        rnBridge.SendFaceDetectedEvent(faceDetected, faceCount, totalTrackables, trackingStates);
        lastSentFaceCount = faceCount;
        lastSentTotalTrackables = totalTrackables;
        lastSentTrackingStates = trackingStates;
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
