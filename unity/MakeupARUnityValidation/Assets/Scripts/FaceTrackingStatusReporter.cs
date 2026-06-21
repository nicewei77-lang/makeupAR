using System.Globalization;
using System.Reflection;
using System.Text;
using Unity.XR.CoreUtils;
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
    [SerializeField] private XROrigin xrOrigin;
    [SerializeField] private Camera arCamera;
    [SerializeField] private float logIntervalSeconds = 1.0f;
    [SerializeField] private bool drawDebugOverlay = true;
    [SerializeField] private bool logE1Diagnostics = true;

    private int lastFaceCount = -1;
    private int lastTotalTrackables = -1;
    private int lastSentFaceCount = -1;
    private int lastSentTotalTrackables = -1;
    private int trackablesChangedCount;
    private string faceSupportState = "Unknown";
    private string lastTrackingStates = string.Empty;
    private string lastSentTrackingStates = string.Empty;
    private float nextLogTime;
    private GUIStyle debugBoxStyle;
    private GUIStyle debugTitleStyle;
    private GUIStyle debugLabelStyle;

    private void Awake()
    {
        RefreshSceneReferences();
        RefreshFaceSupportState();
        LogStatus(true);
    }

    private void OnEnable()
    {
        RefreshSceneReferences();
        ARSession.stateChanged += OnArSessionStateChanged;

        if (faceManager != null)
        {
            faceManager.trackablesChanged.AddListener(OnFaceTrackablesChanged);
        }
    }

    private void OnDisable()
    {
        ARSession.stateChanged -= OnArSessionStateChanged;

        if (faceManager != null)
        {
            faceManager.trackablesChanged.RemoveListener(OnFaceTrackablesChanged);
        }
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
        GUILayout.BeginArea(new Rect(24, 24, 1060, 560), debugBoxStyle);
        GUILayout.Label("Makeup AR Unity E1", debugTitleStyle);
        GUILayout.Label("AR: " + ARSession.state, debugLabelStyle);
        GUILayout.Label("Orientation: " + Screen.orientation + " " + Screen.width + "x" + Screen.height, debugLabelStyle);
        GUILayout.Label(GetCameraDirectionStatus(), debugLabelStyle);
        GUILayout.Label("Tracked faces: " + faceCount + " / total " + totalTrackables, debugLabelStyle);
        GUILayout.Label("Tracking states: " + trackingStates, debugLabelStyle);
        GUILayout.Label("Face detected: " + faceDetected.ToString().ToLowerInvariant(), debugLabelStyle);
        GUILayout.Label("Pose: " + BuildCompactTransformDiagnostics(), debugLabelStyle);
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
        return CountTrackedFaces(out totalTrackables, out trackingStates, out _);
    }

    private int CountTrackedFaces(out int totalTrackables, out string trackingStates, out string faceDiagnostics)
    {
        totalTrackables = 0;

        if (faceManager == null)
        {
            trackingStates = "faceManager:null";
            faceDiagnostics = "faceManager:null";
            return 0;
        }

        int count = 0;
        StringBuilder stateBuilder = new StringBuilder();
        StringBuilder diagnosticsBuilder = new StringBuilder();

        foreach (ARFace face in faceManager.trackables)
        {
            if (totalTrackables > 0)
            {
                stateBuilder.Append(",");
                diagnosticsBuilder.Append(" | ");
            }

            stateBuilder
                .Append(face.trackableId)
                .Append(":")
                .Append(face.trackingState);

            diagnosticsBuilder
                .Append("id=")
                .Append(face.trackableId)
                .Append(" state=")
                .Append(face.trackingState)
                .Append(" localPos=")
                .Append(FormatVector3(face.transform.localPosition))
                .Append(" worldPos=")
                .Append(FormatVector3(face.transform.position))
                .Append(" euler=")
                .Append(FormatVector3(face.transform.eulerAngles))
                .Append(" mesh=")
                .Append(GetFaceMeshSummary(face));

            totalTrackables++;

            if (face.trackingState == TrackingState.Tracking)
            {
                count++;
            }
        }

        trackingStates = totalTrackables == 0 ? "none" : stateBuilder.ToString();
        faceDiagnostics = totalTrackables == 0 ? "none" : diagnosticsBuilder.ToString();
        return count;
    }

    private void LogStatus(bool force)
    {
        RefreshFaceSupportState();

        int faceCount = CountTrackedFaces(out int totalTrackables, out string trackingStates, out string faceDiagnostics);
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

            if (logE1Diagnostics)
            {
                Debug.Log(
                    "[E1] alignment_diagnostics"
                    + " orientation=" + Screen.orientation
                    + " screen=" + Screen.width.ToString(CultureInfo.InvariantCulture) + "x" + Screen.height.ToString(CultureInfo.InvariantCulture)
                    + "; " + BuildTransformDiagnostics()
                    + "; faces=" + faceDiagnostics);
            }

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

    private void OnFaceTrackablesChanged(ARTrackablesChangedEventArgs<ARFace> args)
    {
        trackablesChangedCount++;
        Debug.Log(
            "[E1] face_trackables_changed"
            + " seq=" + trackablesChangedCount.ToString(CultureInfo.InvariantCulture)
            + " added=" + args.added.Count.ToString(CultureInfo.InvariantCulture)
            + " updated=" + args.updated.Count.ToString(CultureInfo.InvariantCulture)
            + " removed=" + args.removed.Count.ToString(CultureInfo.InvariantCulture)
            + " addedFaces=" + FormatTrackableList(args.added)
            + " updatedFaces=" + FormatTrackableList(args.updated)
            + " removedFaces=" + FormatRemovedTrackableList(args.removed));

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

    private void RefreshSceneReferences()
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

        if (xrOrigin == null)
        {
            xrOrigin = FindFirstObjectByType<XROrigin>();
        }

        if (arCamera == null)
        {
            arCamera = cameraManager != null
                ? cameraManager.GetComponent<Camera>()
                : Camera.main;
        }
    }

    private string BuildTransformDiagnostics()
    {
        RefreshSceneReferences();

        return "xrOrigin=" + FormatTransform(xrOrigin != null ? xrOrigin.transform : null)
            + "; cameraOffset=" + FormatTransform(xrOrigin != null && xrOrigin.CameraFloorOffsetObject != null ? xrOrigin.CameraFloorOffsetObject.transform : null)
            + "; arCamera=" + FormatTransform(arCamera != null ? arCamera.transform : null);
    }

    private string BuildCompactTransformDiagnostics()
    {
        RefreshSceneReferences();

        string cameraPosition = arCamera != null ? FormatVector3(arCamera.transform.localPosition) : "camera:null";
        string originPosition = xrOrigin != null ? FormatVector3(xrOrigin.transform.position) : "origin:null";
        return "origin " + originPosition + " cameraLocal " + cameraPosition;
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

    private static string FormatTransform(Transform target)
    {
        if (target == null)
        {
            return "null";
        }

        return target.name
            + " localPos=" + FormatVector3(target.localPosition)
            + " localEuler=" + FormatVector3(target.localEulerAngles)
            + " worldPos=" + FormatVector3(target.position)
            + " worldEuler=" + FormatVector3(target.eulerAngles);
    }

    private static string GetFaceMeshSummary(ARFace face)
    {
        if (face == null)
        {
            return "face:null";
        }

        int vertexCount = face.vertices.IsCreated ? face.vertices.Length : -1;
        int indexCount = face.indices.IsCreated ? face.indices.Length : -1;
        int uvCount = face.uvs.IsCreated ? face.uvs.Length : -1;

        MeshFilter meshFilter = face.GetComponent<MeshFilter>();
        Mesh mesh = meshFilter != null ? meshFilter.sharedMesh : null;
        int unityVertexCount = mesh != null ? mesh.vertexCount : -1;

        return "v=" + vertexCount.ToString(CultureInfo.InvariantCulture)
            + ",i=" + indexCount.ToString(CultureInfo.InvariantCulture)
            + ",uv=" + uvCount.ToString(CultureInfo.InvariantCulture)
            + ",meshV=" + unityVertexCount.ToString(CultureInfo.InvariantCulture);
    }

    private static string FormatTrackableList(Unity.XR.CoreUtils.Collections.ReadOnlyList<ARFace> faces)
    {
        if (faces == null || faces.Count == 0)
        {
            return "none";
        }

        StringBuilder builder = new StringBuilder();
        for (int index = 0; index < faces.Count; index++)
        {
            if (index > 0)
            {
                builder.Append("|");
            }

            ARFace face = faces[index];
            builder
                .Append(face.trackableId)
                .Append(":")
                .Append(face.trackingState)
                .Append(":")
                .Append(GetFaceMeshSummary(face));
        }

        return builder.ToString();
    }

    private static string FormatRemovedTrackableList(Unity.XR.CoreUtils.Collections.ReadOnlyList<System.Collections.Generic.KeyValuePair<TrackableId, ARFace>> removedFaces)
    {
        if (removedFaces == null || removedFaces.Count == 0)
        {
            return "none";
        }

        StringBuilder builder = new StringBuilder();
        for (int index = 0; index < removedFaces.Count; index++)
        {
            if (index > 0)
            {
                builder.Append("|");
            }

            builder.Append(removedFaces[index].Key);
        }

        return builder.ToString();
    }

    private static string FormatVector3(Vector3 value)
    {
        return "("
            + value.x.ToString("0.###", CultureInfo.InvariantCulture)
            + ","
            + value.y.ToString("0.###", CultureInfo.InvariantCulture)
            + ","
            + value.z.ToString("0.###", CultureInfo.InvariantCulture)
            + ")";
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
