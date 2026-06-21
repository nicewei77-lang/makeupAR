using System;
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
    [SerializeField] private bool logE2LifecycleDiagnostics = true;

    private int lastFaceCount = -1;
    private int lastTotalTrackables = -1;
    private int lastSentFaceCount = -1;
    private int lastSentTotalTrackables = -1;
    private int trackablesChangedCount;
    private string faceSupportState = "Unknown";
    private string lastTrackingStates = string.Empty;
    private string lastSentTrackingStates = string.Empty;
    private string lastLifecycleEventFingerprint = string.Empty;
    private string previousActiveFaceId = string.Empty;
    private string lastTrackedFaceId = "none";
    private bool hasEverTrackedFace;
    private bool wasFaceLostAfterTracking;
    private float nextLifecycleEventTime;
    private float nextLogTime;
    private GUIStyle debugBoxStyle;
    private GUIStyle debugTitleStyle;
    private GUIStyle debugLabelStyle;

    private sealed class FaceLifecycleSnapshot
    {
        public string Timestamp = string.Empty;
        public string Phase = string.Empty;
        public string Status = "lost";
        public string ActiveFaceId = "none";
        public string PreviousActiveFaceId = "none";
        public string LastTrackedFaceId = "none";
        public string TrackingState = "None";
        public string TrackingStates = "none";
        public string FaceTransform = "none";
        public string MeshSummary = "none";
        public string ProviderCapabilitySnapshot = "unknown";
        public string AddedFaces = "none";
        public string UpdatedFaces = "none";
        public string RemovedFaces = "none";
        public int Sequence;
        public int AddedCount;
        public int UpdatedCount;
        public int RemovedCount;
        public int FaceCount;
        public int TotalTrackables;
        public bool Tracked;
        public bool ActiveFaceChanged;
    }

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
        GUILayout.Label("Makeup AR Unity E2", debugTitleStyle);
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

    private FaceLifecycleSnapshot BuildLifecycleSnapshot(
        string phase,
        int addedCount,
        int updatedCount,
        int removedCount,
        string addedFaces,
        string updatedFaces,
        string removedFaces)
    {
        FaceLifecycleSnapshot snapshot = new FaceLifecycleSnapshot
        {
            Timestamp = GetUtcTimestamp(),
            Phase = phase,
            Sequence = trackablesChangedCount,
            AddedCount = addedCount,
            UpdatedCount = updatedCount,
            RemovedCount = removedCount,
            AddedFaces = addedFaces,
            UpdatedFaces = updatedFaces,
            RemovedFaces = removedFaces,
            ProviderCapabilitySnapshot = faceSupportState,
            LastTrackedFaceId = lastTrackedFaceId,
            PreviousActiveFaceId = string.IsNullOrEmpty(previousActiveFaceId)
                ? "none"
                : previousActiveFaceId
        };

        ARFace activeFace = SelectActiveFace(
            out int faceCount,
            out int totalTrackables,
            out string trackingStates);

        snapshot.FaceCount = faceCount;
        snapshot.TotalTrackables = totalTrackables;
        snapshot.TrackingStates = trackingStates;

        if (activeFace == null)
        {
            snapshot.Status = "lost";
            snapshot.TrackingState = "None";
            snapshot.ActiveFaceId = "none";
            snapshot.Tracked = false;
            snapshot.ActiveFaceChanged = previousActiveFaceId != string.Empty
                && previousActiveFaceId != "none";
            return snapshot;
        }

        snapshot.ActiveFaceId = activeFace.trackableId.ToString();
        snapshot.TrackingState = activeFace.trackingState.ToString();
        snapshot.Tracked = activeFace.trackingState == TrackingState.Tracking;
        snapshot.FaceTransform = FormatTransform(activeFace.transform);
        snapshot.MeshSummary = GetFaceMeshSummary(activeFace);
        snapshot.ActiveFaceChanged = snapshot.ActiveFaceId != snapshot.LastTrackedFaceId
            && snapshot.LastTrackedFaceId != "none";

        if (snapshot.Tracked && wasFaceLostAfterTracking && hasEverTrackedFace)
        {
            snapshot.Status = "reacquired";
        }
        else if (snapshot.Tracked)
        {
            snapshot.Status = "tracking";
        }
        else if (activeFace.trackingState == TrackingState.Limited)
        {
            snapshot.Status = "limited";
        }
        else
        {
            snapshot.Status = "lost";
        }

        return snapshot;
    }

    private ARFace SelectActiveFace(
        out int faceCount,
        out int totalTrackables,
        out string trackingStates)
    {
        faceCount = CountTrackedFaces(out totalTrackables, out trackingStates);

        if (faceManager == null)
        {
            return null;
        }

        ARFace fallbackFace = null;
        ARFace limitedFace = null;

        foreach (ARFace face in faceManager.trackables)
        {
            if (face.trackingState == TrackingState.Tracking)
            {
                return face;
            }

            if (face.trackingState == TrackingState.Limited && limitedFace == null)
            {
                limitedFace = face;
            }

            if (fallbackFace == null)
            {
                fallbackFace = face;
            }
        }

        return limitedFace != null ? limitedFace : fallbackFace;
    }

    private string BuildFaceDiagnosticsSummary()
    {
        CountTrackedFaces(out _, out _, out string faceDiagnostics);
        return faceDiagnostics;
    }

    private void LogStatus(bool force)
    {
        LogStatus(
            force,
            "status",
            0,
            0,
            0,
            "none",
            "none",
            "none");
    }

    private void LogStatus(
        bool force,
        string phase,
        int addedCount,
        int updatedCount,
        int removedCount,
        string addedFaces,
        string updatedFaces,
        string removedFaces)
    {
        RefreshFaceSupportState();

        FaceLifecycleSnapshot lifecycle = BuildLifecycleSnapshot(
            phase,
            addedCount,
            updatedCount,
            removedCount,
            addedFaces,
            updatedFaces,
            removedFaces);

        bool faceDetected = lifecycle.FaceCount > 0;

        if (force
            || lifecycle.FaceCount != lastFaceCount
            || lifecycle.TotalTrackables != lastTotalTrackables
            || lifecycle.TrackingStates != lastTrackingStates
            || Time.unscaledTime >= nextLogTime)
        {
            Debug.Log(
                "[M1] AR support state: " + ARSession.state
                + "; " + GetCameraDirectionStatus()
                + "; Face tracking support state: " + faceSupportState
                + "; Current tracked face count: " + lifecycle.FaceCount
                + "; Total face trackables: " + lifecycle.TotalTrackables
                + "; Face tracking states: " + lifecycle.TrackingStates
                + "; Face detected: " + faceDetected.ToString().ToLowerInvariant());

            if (logE1Diagnostics)
            {
                Debug.Log(
                    "[E1] alignment_diagnostics"
                    + " orientation=" + Screen.orientation
                    + " screen=" + Screen.width.ToString(CultureInfo.InvariantCulture) + "x" + Screen.height.ToString(CultureInfo.InvariantCulture)
                    + "; " + BuildTransformDiagnostics()
                    + "; faces=" + BuildFaceDiagnosticsSummary());
            }

            if (logE2LifecycleDiagnostics)
            {
                Debug.Log("[E2] face_lifecycle " + FormatLifecycleSnapshotForLog(lifecycle));
            }

            lastFaceCount = lifecycle.FaceCount;
            lastTotalTrackables = lifecycle.TotalTrackables;
            lastTrackingStates = lifecycle.TrackingStates;
            nextLogTime = Time.unscaledTime + logIntervalSeconds;
        }

        SendFaceStateToReactNative(
            faceDetected,
            lifecycle.FaceCount,
            lifecycle.TotalTrackables,
            lifecycle.TrackingStates,
            force);
        SendFaceLifecycleToReactNative(lifecycle, force);
        UpdateLifecycleMemory(lifecycle);
    }

    private void OnArSessionStateChanged(ARSessionStateChangedEventArgs args)
    {
        Debug.Log("[M1] AR support state changed: " + args.state);
        LogStatus(true);
    }

    private void OnFaceTrackablesChanged(ARTrackablesChangedEventArgs<ARFace> args)
    {
        trackablesChangedCount++;
        string timestamp = GetUtcTimestamp();
        string addedFaces = FormatTrackableList(args.added);
        string updatedFaces = FormatTrackableList(args.updated);
        string removedFaces = FormatRemovedTrackableList(args.removed);

        Debug.Log(
            "[E1] face_trackables_changed"
            + " seq=" + trackablesChangedCount.ToString(CultureInfo.InvariantCulture)
            + " added=" + args.added.Count.ToString(CultureInfo.InvariantCulture)
            + " updated=" + args.updated.Count.ToString(CultureInfo.InvariantCulture)
            + " removed=" + args.removed.Count.ToString(CultureInfo.InvariantCulture)
            + " addedFaces=" + addedFaces
            + " updatedFaces=" + updatedFaces
            + " removedFaces=" + removedFaces);

        Debug.Log(
            "[E2] trackablesChanged"
            + " timestamp=" + timestamp
            + " seq=" + trackablesChangedCount.ToString(CultureInfo.InvariantCulture)
            + " trackablesChanged.added=" + args.added.Count.ToString(CultureInfo.InvariantCulture)
            + " trackablesChanged.updated=" + args.updated.Count.ToString(CultureInfo.InvariantCulture)
            + " trackablesChanged.removed=" + args.removed.Count.ToString(CultureInfo.InvariantCulture)
            + " addedFaces=" + addedFaces
            + " updatedFaces=" + updatedFaces
            + " removedFaces=" + removedFaces);

        LogStatus(
            true,
            "trackablesChanged",
            args.added.Count,
            args.updated.Count,
            args.removed.Count,
            addedFaces,
            updatedFaces,
            removedFaces);
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

    private void SendFaceLifecycleToReactNative(FaceLifecycleSnapshot lifecycle, bool force)
    {
        if (rnBridge == null)
        {
            rnBridge = FindFirstObjectByType<RNBridge>();
        }

        if (rnBridge == null)
        {
            Debug.LogWarning("[E2] face_lifecycle_send_skipped RNBridge not found");
            return;
        }

        string fingerprint = lifecycle.Status
            + "|active=" + lifecycle.ActiveFaceId
            + "|state=" + lifecycle.TrackingState
            + "|count=" + lifecycle.FaceCount.ToString(CultureInfo.InvariantCulture)
            + "|total=" + lifecycle.TotalTrackables.ToString(CultureInfo.InvariantCulture)
            + "|trackingStates=" + lifecycle.TrackingStates
            + "|changed=" + lifecycle.AddedCount.ToString(CultureInfo.InvariantCulture)
            + "," + lifecycle.UpdatedCount.ToString(CultureInfo.InvariantCulture)
            + "," + lifecycle.RemovedCount.ToString(CultureInfo.InvariantCulture);

        if (!force
            && fingerprint == lastLifecycleEventFingerprint
            && Time.unscaledTime < nextLifecycleEventTime)
        {
            return;
        }

        rnBridge.SendFaceLifecycleEvent(BuildLifecycleJson(lifecycle));
        lastLifecycleEventFingerprint = fingerprint;
        nextLifecycleEventTime = Time.unscaledTime + logIntervalSeconds;
    }

    private void UpdateLifecycleMemory(FaceLifecycleSnapshot lifecycle)
    {
        previousActiveFaceId = lifecycle.ActiveFaceId;

        if (lifecycle.Tracked)
        {
            hasEverTrackedFace = true;
            lastTrackedFaceId = lifecycle.ActiveFaceId;
            wasFaceLostAfterTracking = false;
            return;
        }

        if (lifecycle.Status == "lost" && hasEverTrackedFace)
        {
            wasFaceLostAfterTracking = true;
        }
    }

    private static string FormatLifecycleSnapshotForLog(FaceLifecycleSnapshot lifecycle)
    {
        return "timestamp=" + lifecycle.Timestamp
            + " phase=" + lifecycle.Phase
            + " seq=" + lifecycle.Sequence.ToString(CultureInfo.InvariantCulture)
            + " status=" + lifecycle.Status
            + " selectedActiveFaceId=" + lifecycle.ActiveFaceId
            + " previousActiveFaceId=" + lifecycle.PreviousActiveFaceId
            + " lastTrackedFaceId=" + lifecycle.LastTrackedFaceId
            + " activeFaceChanged=" + lifecycle.ActiveFaceChanged.ToString().ToLowerInvariant()
            + " trackingState=" + lifecycle.TrackingState
            + " tracked=" + lifecycle.Tracked.ToString().ToLowerInvariant()
            + " faceCount=" + lifecycle.FaceCount.ToString(CultureInfo.InvariantCulture)
            + " totalTrackables=" + lifecycle.TotalTrackables.ToString(CultureInfo.InvariantCulture)
            + " trackingStates=" + lifecycle.TrackingStates
            + " trackablesChanged.added=" + lifecycle.AddedCount.ToString(CultureInfo.InvariantCulture)
            + " trackablesChanged.updated=" + lifecycle.UpdatedCount.ToString(CultureInfo.InvariantCulture)
            + " trackablesChanged.removed=" + lifecycle.RemovedCount.ToString(CultureInfo.InvariantCulture)
            + " faceTransform=" + lifecycle.FaceTransform
            + " mesh=" + lifecycle.MeshSummary
            + " provider=\"" + lifecycle.ProviderCapabilitySnapshot + "\"";
    }

    private static string BuildLifecycleJson(FaceLifecycleSnapshot lifecycle)
    {
        return "{"
            + "\"type\":\"face_lifecycle\""
            + ",\"timestamp\":\"" + EscapeJsonString(lifecycle.Timestamp) + "\""
            + ",\"phase\":\"" + EscapeJsonString(lifecycle.Phase) + "\""
            + ",\"sequence\":" + lifecycle.Sequence.ToString(CultureInfo.InvariantCulture)
            + ",\"status\":\"" + EscapeJsonString(lifecycle.Status) + "\""
            + ",\"selectedActiveFaceId\":\"" + EscapeJsonString(lifecycle.ActiveFaceId) + "\""
            + ",\"previousActiveFaceId\":\"" + EscapeJsonString(lifecycle.PreviousActiveFaceId) + "\""
            + ",\"lastTrackedFaceId\":\"" + EscapeJsonString(lifecycle.LastTrackedFaceId) + "\""
            + ",\"activeFaceChanged\":" + lifecycle.ActiveFaceChanged.ToString().ToLowerInvariant()
            + ",\"tracked\":" + lifecycle.Tracked.ToString().ToLowerInvariant()
            + ",\"trackingState\":\"" + EscapeJsonString(lifecycle.TrackingState) + "\""
            + ",\"faceCount\":" + lifecycle.FaceCount.ToString(CultureInfo.InvariantCulture)
            + ",\"totalTrackables\":" + lifecycle.TotalTrackables.ToString(CultureInfo.InvariantCulture)
            + ",\"trackingStates\":\"" + EscapeJsonString(lifecycle.TrackingStates) + "\""
            + ",\"addedCount\":" + lifecycle.AddedCount.ToString(CultureInfo.InvariantCulture)
            + ",\"updatedCount\":" + lifecycle.UpdatedCount.ToString(CultureInfo.InvariantCulture)
            + ",\"removedCount\":" + lifecycle.RemovedCount.ToString(CultureInfo.InvariantCulture)
            + ",\"addedFaces\":\"" + EscapeJsonString(lifecycle.AddedFaces) + "\""
            + ",\"updatedFaces\":\"" + EscapeJsonString(lifecycle.UpdatedFaces) + "\""
            + ",\"removedFaces\":\"" + EscapeJsonString(lifecycle.RemovedFaces) + "\""
            + ",\"faceTransform\":\"" + EscapeJsonString(lifecycle.FaceTransform) + "\""
            + ",\"meshSummary\":\"" + EscapeJsonString(lifecycle.MeshSummary) + "\""
            + ",\"providerCapabilitySnapshot\":\"" + EscapeJsonString(lifecycle.ProviderCapabilitySnapshot) + "\""
            + "}";
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

    private static string GetUtcTimestamp()
    {
        return DateTimeOffset.UtcNow.ToString("o", CultureInfo.InvariantCulture);
    }

    private static string EscapeJsonString(string value)
    {
        return (value ?? string.Empty)
            .Replace("\\", "\\\\")
            .Replace("\"", "\\\"");
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
