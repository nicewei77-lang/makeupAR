using System;
using System.Globalization;
using System.Reflection;
using System.Text;
using Unity.XR.CoreUtils;
using UnityEngine;
using UnityEngine.Profiling;
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
    [SerializeField] private float logIntervalSeconds = 2.0f;
    [SerializeField] private bool drawDebugOverlay;
    [SerializeField] private bool logE1Diagnostics = true;
    [SerializeField] private bool logE2LifecycleDiagnostics = true;
    [SerializeField] private bool logE7MetricSamples = true;
    [SerializeField] private float e7MetricIntervalSeconds = 2.0f;

    private int lastFaceCount = -1;
    private int lastTotalTrackables = -1;
    private int lastSentFaceCount = -1;
    private int lastSentTotalTrackables = -1;
    private int trackablesChangedCount;
    private string faceSupportState = "Unknown";
    private string lastTrackingStates = string.Empty;
    private string lastSentTrackingStates = string.Empty;
    private string lastLifecycleEventFingerprint = string.Empty;
    private string lastFeatureSnapshotFingerprint = string.Empty;
    private string previousActiveFaceId = string.Empty;
    private string lastTrackedFaceId = "none";
    private bool hasEverTrackedFace;
    private bool wasFaceLostAfterTracking;
    private float nextLifecycleEventTime;
    private float nextFeatureSnapshotEventTime;
    private float nextLogTime;
    private string e7RunId = string.Empty;
    private float e7MetricWindowStartTime;
    private int e7MetricFrameCount;
    private float e7MetricFrameTimeTotalMs;
    private float e7MetricWorstFrameTimeMs;
    private bool e7SustainedSub20FpsObserved;
    private bool e7MemoryUnavailableLogged;
    private bool e7ThermalUnavailableLogged;
    private GUIStyle debugBoxStyle;
    private GUIStyle debugTitleStyle;
    private GUIStyle debugLabelStyle;

    public bool DebugOverlayVisible
    {
        get { return drawDebugOverlay; }
    }

    public void SetDebugOverlayVisible(bool visible)
    {
        drawDebugOverlay = visible;
    }

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
        public string PosePositionJson = "[0,0,0]";
        public string PoseRotationEulerJson = "[0,0,0]";
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
        public int MeshVertexCount;
        public int MeshIndexCount;
        public int MeshUvCount;
        public int UnityMeshVertexCount;
        public bool Tracked;
        public bool ActiveFaceChanged;
        public bool PoseAvailable;
        public bool HasStableUv;
    }

    private void Awake()
    {
        RefreshSceneReferences();
        RefreshFaceSupportState();
        InitializeE7MetricSamples();
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
        UpdateE7MetricSampler();

        int faceCount = CountTrackedFaces(out int totalTrackables, out string trackingStates);
        bool faceCountChanged = faceCount != lastFaceCount
            || totalTrackables != lastTotalTrackables
            || trackingStates != lastTrackingStates;

        if (faceCountChanged || Time.unscaledTime >= nextLogTime)
        {
            LogStatus(false);
        }
    }

    private void InitializeE7MetricSamples()
    {
        if (!string.IsNullOrWhiteSpace(e7RunId))
        {
            return;
        }

        e7RunId = "smooth-mask-" + DateTimeOffset.Now.ToString("yyyy-MM-dd", CultureInfo.InvariantCulture);
        e7MetricWindowStartTime = Time.unscaledTime;
        e7MetricFrameCount = 0;
        e7MetricFrameTimeTotalMs = 0.0f;
        e7MetricWorstFrameTimeMs = 0.0f;
        e7SustainedSub20FpsObserved = false;
        LogE7ThermalUnavailableOnce();
    }

    private void UpdateE7MetricSampler()
    {
        if (!logE7MetricSamples)
        {
            return;
        }

        InitializeE7MetricSamples();

        float frameTimeMs = Mathf.Max(0.0f, Time.unscaledDeltaTime * 1000.0f);
        e7MetricFrameCount++;
        e7MetricFrameTimeTotalMs += frameTimeMs;
        e7MetricWorstFrameTimeMs = Mathf.Max(e7MetricWorstFrameTimeMs, frameTimeMs);
        e7SustainedSub20FpsObserved = e7SustainedSub20FpsObserved || frameTimeMs >= 50.0f;

        float elapsedSeconds = Time.unscaledTime - e7MetricWindowStartTime;
        if (elapsedSeconds < Mathf.Max(0.5f, e7MetricIntervalSeconds)
            || e7MetricFrameCount <= 0)
        {
            return;
        }

        LogE7MetricSample(elapsedSeconds);

        e7MetricWindowStartTime = Time.unscaledTime;
        e7MetricFrameCount = 0;
        e7MetricFrameTimeTotalMs = 0.0f;
        e7MetricWorstFrameTimeMs = 0.0f;
        e7SustainedSub20FpsObserved = false;
    }

    private void LogE7MetricSample(float elapsedSeconds)
    {
        RefreshFaceSupportState();

        FaceLifecycleSnapshot lifecycle = BuildLifecycleSnapshot(
            "e7MetricSample",
            0,
            0,
            0,
            "none",
            "none",
            "none");

        if (rnBridge == null)
        {
            rnBridge = FindFirstObjectByType<RNBridge>();
        }

        long timestampMs = DateTimeOffset.UtcNow.ToUnixTimeMilliseconds();
        string metricPhase = rnBridge != null ? rnBridge.GetE7MetricPhase() : "smooth_mask";
        string metricRunId = !string.IsNullOrWhiteSpace(e7RunId)
            ? e7RunId
            : "smooth-mask-" + DateTimeOffset.Now.ToString("yyyy-MM-dd", CultureInfo.InvariantCulture);
        string unityFrameworkBuildLabel = "e7-smooth-mask";
        int sampleWindowMs = Mathf.RoundToInt(elapsedSeconds * 1000.0f);
        float averageFrameTimeMs = e7MetricFrameTimeTotalMs / Mathf.Max(1, e7MetricFrameCount);
        float averageFps = e7MetricFrameCount / Mathf.Max(0.001f, elapsedSeconds);
        bool sustainedSub20FpsObserved = e7SustainedSub20FpsObserved || averageFps < 20.0f;

        bool memoryMetricAvailable = TryCollectMemoryMetrics(
            out long allocatedMemoryBytes,
            out long reservedMemoryBytes,
            out long monoUsedMemoryBytes);
        string memoryMetricSource = memoryMetricAvailable
            ? "UnityEngine.Profiling.Profiler"
            : "manual-unavailable";

        if (!memoryMetricAvailable)
        {
            LogE7MemoryUnavailableOnce();
        }

        LogE7ThermalUnavailableOnce();

        string smoothMaskLogFields = rnBridge != null
            ? rnBridge.BuildE7SmoothMaskStateLogFields()
            : " rendererMode=smooth-region-mask lookId=smooth_region_mask region=none activeRegions=none texture=none sample=none color=none opacity=0";
        string smoothMaskJsonFragment = rnBridge != null
            ? rnBridge.BuildE7SmoothMaskStateJsonFragment()
            : "\"rendererMode\":\"smooth-region-mask\",\"lookId\":\"smooth_region_mask\",\"region\":\"none\",\"activeRegions\":\"none\",\"texture\":\"none\",\"sample\":\"none\",\"color\":\"none\",\"opacity\":0";

        Debug.Log(
            "[E7] metric_sample"
            + " runId=" + metricRunId
            + " phase=" + metricPhase
            + " timestampMs=" + timestampMs.ToString(CultureInfo.InvariantCulture)
            + " deviceName=" + SanitizeLogValue(SystemInfo.deviceName)
            + " appBuildLabel=" + SanitizeLogValue(Application.version)
            + " unityFrameworkBuildLabel=" + unityFrameworkBuildLabel
            + smoothMaskLogFields
            + " trackingState=" + lifecycle.TrackingState
            + " faceCount=" + lifecycle.FaceCount.ToString(CultureInfo.InvariantCulture)
            + " totalTrackables=" + lifecycle.TotalTrackables.ToString(CultureInfo.InvariantCulture)
            + " activeTrackableState=" + lifecycle.Status
            + " meshVertexCount=" + lifecycle.MeshVertexCount.ToString(CultureInfo.InvariantCulture)
            + " meshIndexCount=" + lifecycle.MeshIndexCount.ToString(CultureInfo.InvariantCulture)
            + " meshUvCount=" + lifecycle.MeshUvCount.ToString(CultureInfo.InvariantCulture)
            + " hasStableUv=" + lifecycle.HasStableUv.ToString().ToLowerInvariant()
            + " meshSummary=" + SanitizeLogValue(lifecycle.MeshSummary)
            + " sampleWindowMs=" + sampleWindowMs.ToString(CultureInfo.InvariantCulture)
            + " sampleFrameCount=" + e7MetricFrameCount.ToString(CultureInfo.InvariantCulture)
            + " averageFps=" + averageFps.ToString("0.0", CultureInfo.InvariantCulture)
            + " averageFrameTimeMs=" + averageFrameTimeMs.ToString("0.0", CultureInfo.InvariantCulture)
            + " worstFrameTimeMs=" + e7MetricWorstFrameTimeMs.ToString("0.0", CultureInfo.InvariantCulture)
            + " sustainedSub20FpsObserved=" + sustainedSub20FpsObserved.ToString().ToLowerInvariant()
            + " memoryMetricAvailable=" + memoryMetricAvailable.ToString().ToLowerInvariant()
            + " memoryMetricSource=" + memoryMetricSource
            + " allocatedMemoryMb=" + FormatMegabytes(allocatedMemoryBytes)
            + " reservedMemoryMb=" + FormatMegabytes(reservedMemoryBytes)
            + " monoUsedMemoryMb=" + FormatMegabytes(monoUsedMemoryBytes)
            + " memoryWarningObserved=false"
            + " memoryMetricYellowCap=" + (!memoryMetricAvailable).ToString().ToLowerInvariant()
            + " thermalEvidenceType=manual-device-heat"
            + " thermalWarningObserved=false"
            + " manualHeatObservation=not_recorded"
            + " thermalMetricYellowCap=true");

        if (rnBridge != null)
        {
            rnBridge.SendE7MetricSampleEvent(
                "{"
                + "\"type\":\"e7_metric_sample\""
                + ",\"runId\":\"" + EscapeJsonString(metricRunId) + "\""
                + ",\"phase\":\"" + EscapeJsonString(metricPhase) + "\""
                + ",\"timestampMs\":" + timestampMs.ToString(CultureInfo.InvariantCulture)
                + ",\"deviceName\":\"" + EscapeJsonString(SystemInfo.deviceName) + "\""
                + ",\"appBuildLabel\":\"" + EscapeJsonString(Application.version) + "\""
                + ",\"unityFrameworkBuildLabel\":\"" + EscapeJsonString(unityFrameworkBuildLabel) + "\""
                + "," + smoothMaskJsonFragment
                + ",\"trackingState\":\"" + EscapeJsonString(lifecycle.TrackingState) + "\""
                + ",\"faceCount\":" + lifecycle.FaceCount.ToString(CultureInfo.InvariantCulture)
                + ",\"totalTrackables\":" + lifecycle.TotalTrackables.ToString(CultureInfo.InvariantCulture)
                + ",\"activeTrackableState\":\"" + EscapeJsonString(lifecycle.Status) + "\""
                + ",\"meshVertexCount\":" + lifecycle.MeshVertexCount.ToString(CultureInfo.InvariantCulture)
                + ",\"meshIndexCount\":" + lifecycle.MeshIndexCount.ToString(CultureInfo.InvariantCulture)
                + ",\"meshUvCount\":" + lifecycle.MeshUvCount.ToString(CultureInfo.InvariantCulture)
                + ",\"hasStableUv\":" + lifecycle.HasStableUv.ToString().ToLowerInvariant()
                + ",\"meshSummary\":\"" + EscapeJsonString(lifecycle.MeshSummary) + "\""
                + ",\"sampleWindowMs\":" + sampleWindowMs.ToString(CultureInfo.InvariantCulture)
                + ",\"sampleFrameCount\":" + e7MetricFrameCount.ToString(CultureInfo.InvariantCulture)
                + ",\"averageFps\":" + averageFps.ToString("0.0", CultureInfo.InvariantCulture)
                + ",\"averageFrameTimeMs\":" + averageFrameTimeMs.ToString("0.0", CultureInfo.InvariantCulture)
                + ",\"worstFrameTimeMs\":" + e7MetricWorstFrameTimeMs.ToString("0.0", CultureInfo.InvariantCulture)
                + ",\"sustainedSub20FpsObserved\":" + sustainedSub20FpsObserved.ToString().ToLowerInvariant()
                + ",\"memoryMetricAvailable\":" + memoryMetricAvailable.ToString().ToLowerInvariant()
                + ",\"memoryMetricSource\":\"" + EscapeJsonString(memoryMetricSource) + "\""
                + ",\"allocatedMemoryMb\":" + FormatMegabytes(allocatedMemoryBytes)
                + ",\"reservedMemoryMb\":" + FormatMegabytes(reservedMemoryBytes)
                + ",\"monoUsedMemoryMb\":" + FormatMegabytes(monoUsedMemoryBytes)
                + ",\"memoryWarningObserved\":false"
                + ",\"memoryMetricYellowCap\":" + (!memoryMetricAvailable).ToString().ToLowerInvariant()
                + ",\"thermalEvidenceType\":\"manual-device-heat\""
                + ",\"thermalWarningObserved\":false"
                + ",\"manualHeatObservation\":\"not_recorded\""
                + ",\"thermalMetricYellowCap\":true"
                + "}");
        }
    }

    private bool TryCollectMemoryMetrics(
        out long allocatedMemoryBytes,
        out long reservedMemoryBytes,
        out long monoUsedMemoryBytes)
    {
        allocatedMemoryBytes = 0L;
        reservedMemoryBytes = 0L;
        monoUsedMemoryBytes = 0L;

        try
        {
            allocatedMemoryBytes = Profiler.GetTotalAllocatedMemoryLong();
            reservedMemoryBytes = Profiler.GetTotalReservedMemoryLong();
            monoUsedMemoryBytes = Profiler.GetMonoUsedSizeLong();
            return allocatedMemoryBytes > 0L || reservedMemoryBytes > 0L || monoUsedMemoryBytes > 0L;
        }
        catch (Exception exception)
        {
            Debug.LogWarning("[E7] memory_metric_read_failed error=" + exception.Message);
            return false;
        }
    }

    private void LogE7MemoryUnavailableOnce()
    {
        if (e7MemoryUnavailableLogged)
        {
            return;
        }

        Debug.Log(
            "[E7] metric_unavailable"
            + " runId=" + e7RunId
            + " phase=smooth_mask"
            + " metric=memory"
            + " reason=Profiler_counter_unavailable_in_current_build"
            + " memoryMetricAvailable=false"
            + " yellowCap=true");
        e7MemoryUnavailableLogged = true;
    }

    private void LogE7ThermalUnavailableOnce()
    {
        if (e7ThermalUnavailableLogged)
        {
            return;
        }

        Debug.Log(
            "[E7] metric_unavailable"
            + " runId=" + e7RunId
            + " phase=smooth_mask"
            + " metric=thermal"
            + " reason=native_thermal_api_not_configured"
            + " thermalEvidenceType=manual-device-heat"
            + " yellowCap=true");
        e7ThermalUnavailableLogged = true;
    }

    private static string FormatMegabytes(long bytes)
    {
        return (bytes / 1048576.0).ToString("0.0", CultureInfo.InvariantCulture);
    }

    private static string SanitizeLogValue(string value)
    {
        if (string.IsNullOrWhiteSpace(value))
        {
            return "none";
        }

        return value.Trim().Replace(" ", "_").Replace(";", ",");
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
        snapshot.PoseAvailable = true;
        snapshot.PosePositionJson = FormatVector3Json(activeFace.transform.position);
        snapshot.PoseRotationEulerJson = FormatVector3Json(activeFace.transform.eulerAngles);
        snapshot.MeshSummary = GetFaceMeshSummary(activeFace);
        snapshot.MeshVertexCount = GetFaceVertexCount(activeFace);
        snapshot.MeshIndexCount = GetFaceIndexCount(activeFace);
        snapshot.MeshUvCount = GetFaceUvCount(activeFace);
        snapshot.UnityMeshVertexCount = GetUnityMeshVertexCount(activeFace);
        snapshot.HasStableUv = snapshot.MeshUvCount > 0;
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

        ARFace firstUsableFace = null;
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

            if (firstUsableFace == null)
            {
                firstUsableFace = face;
            }
        }

        return limitedFace != null ? limitedFace : firstUsableFace;
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
        SendFaceFeatureSnapshotToReactNative(lifecycle, force);
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
        bool structuralChange = args.added.Count > 0 || args.removed.Count > 0;
        bool shouldLogTrackablesChanged = structuralChange || Time.unscaledTime >= nextLogTime;

        if (shouldLogTrackablesChanged)
        {
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
        }

        LogStatus(
            structuralChange,
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

    private void SendFaceFeatureSnapshotToReactNative(FaceLifecycleSnapshot lifecycle, bool force)
    {
        if (rnBridge == null)
        {
            rnBridge = FindFirstObjectByType<RNBridge>();
        }

        if (rnBridge == null)
        {
            Debug.LogWarning("[E5] face_feature_snapshot_send_skipped RNBridge not found");
            return;
        }

        string regionFingerprint = rnBridge.BuildFaceFeatureRegionSnapshotLogFields();
        string fingerprint = lifecycle.Status
            + "|active=" + lifecycle.ActiveFaceId
            + "|state=" + lifecycle.TrackingState
            + "|count=" + lifecycle.FaceCount.ToString(CultureInfo.InvariantCulture)
            + "|total=" + lifecycle.TotalTrackables.ToString(CultureInfo.InvariantCulture)
            + "|mesh=" + lifecycle.MeshSummary
            + "|regions=" + regionFingerprint;

        if (!force
            && fingerprint == lastFeatureSnapshotFingerprint
            && Time.unscaledTime < nextFeatureSnapshotEventTime)
        {
            return;
        }

        string snapshotJson = BuildFaceFeatureSnapshotJson(lifecycle);
        Debug.Log(
            "[E5] face_feature_snapshot_created"
            + " schemaVersion=1"
            + " timestampMs=" + DateTimeOffset.UtcNow.ToUnixTimeMilliseconds().ToString(CultureInfo.InvariantCulture)
            + " tracked=" + lifecycle.Tracked.ToString().ToLowerInvariant()
            + " faceCount=" + lifecycle.FaceCount.ToString(CultureInfo.InvariantCulture)
            + " trackingState=" + lifecycle.TrackingState
            + " meshVertices=" + lifecycle.MeshVertexCount.ToString(CultureInfo.InvariantCulture)
            + " meshIndices=" + lifecycle.MeshIndexCount.ToString(CultureInfo.InvariantCulture)
            + " meshUvs=" + lifecycle.MeshUvCount.ToString(CultureInfo.InvariantCulture)
            + " rawCameraFrameStored=false"
            + " offDeviceUpload=false"
            + regionFingerprint
            + " snapshotBytes=" + snapshotJson.Length.ToString(CultureInfo.InvariantCulture));

        rnBridge.SendFaceFeatureSnapshotEvent(snapshotJson);
        lastFeatureSnapshotFingerprint = fingerprint;
        nextFeatureSnapshotEventTime = Time.unscaledTime + logIntervalSeconds;
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

    private string BuildFaceFeatureSnapshotJson(FaceLifecycleSnapshot lifecycle)
    {
        long timestampMs = DateTimeOffset.UtcNow.ToUnixTimeMilliseconds();
        string regionSnapshotJson = rnBridge != null
            ? rnBridge.BuildFaceFeatureRegionSnapshotJsonFragment()
            : BuildUnavailableRegionSnapshotJsonFragment();

        return "{"
            + "\"type\":\"face_feature_snapshot\""
            + ",\"schemaVersion\":1"
            + ",\"timestampMs\":" + timestampMs.ToString(CultureInfo.InvariantCulture)
            + ",\"timestamp\":\"" + EscapeJsonString(GetUtcTimestamp()) + "\""
            + ",\"source\":\"arkit_arface\""
            + ",\"deviceModel\":\"" + EscapeJsonString(SystemInfo.deviceModel) + "\""
            + ",\"arSessionState\":\"" + EscapeJsonString(ARSession.state.ToString()) + "\""
            + ",\"cameraFacing\":\"" + EscapeJsonString(GetCurrentCameraFacing()) + "\""
            + ",\"orientation\":\"" + EscapeJsonString(Screen.orientation.ToString()) + "\""
            + ",\"faceDetected\":" + lifecycle.Tracked.ToString().ToLowerInvariant()
            + ",\"tracked\":" + lifecycle.Tracked.ToString().ToLowerInvariant()
            + ",\"faceCount\":" + lifecycle.FaceCount.ToString(CultureInfo.InvariantCulture)
            + ",\"totalTrackables\":" + lifecycle.TotalTrackables.ToString(CultureInfo.InvariantCulture)
            + ",\"trackingStates\":\"" + EscapeJsonString(lifecycle.TrackingStates) + "\""
            + ",\"trackingState\":\"" + EscapeJsonString(lifecycle.TrackingState) + "\""
            + ",\"lifecycleState\":\"" + EscapeJsonString(lifecycle.Status) + "\""
            + ",\"selectedActiveFaceId\":\"" + EscapeJsonString(lifecycle.ActiveFaceId) + "\""
            + ",\"meshSummary\":\"" + EscapeJsonString(lifecycle.MeshSummary) + "\""
            + ",\"providerCapabilitySnapshot\":\"" + EscapeJsonString(lifecycle.ProviderCapabilitySnapshot) + "\""
            + ",\"rawCameraFrameStored\":false"
            + ",\"offDeviceUpload\":false"
            + ",\"activeFace\":{"
            + "\"trackableId\":\"" + EscapeJsonString(lifecycle.ActiveFaceId) + "\""
            + ",\"trackingState\":\"" + EscapeJsonString(lifecycle.TrackingState) + "\""
            + ",\"lifecycleState\":\"" + EscapeJsonString(lifecycle.Status) + "\""
            + ",\"poseAvailable\":" + lifecycle.PoseAvailable.ToString().ToLowerInvariant()
            + ",\"pose\":{"
            + "\"position\":" + lifecycle.PosePositionJson
            + ",\"rotationEuler\":" + lifecycle.PoseRotationEulerJson
            + "}"
            + "}"
            + ",\"mesh\":{"
            + "\"vertexCount\":" + lifecycle.MeshVertexCount.ToString(CultureInfo.InvariantCulture)
            + ",\"indexCount\":" + lifecycle.MeshIndexCount.ToString(CultureInfo.InvariantCulture)
            + ",\"uvCount\":" + lifecycle.MeshUvCount.ToString(CultureInfo.InvariantCulture)
            + ",\"unityMeshVertexCount\":" + lifecycle.UnityMeshVertexCount.ToString(CultureInfo.InvariantCulture)
            + ",\"hasStableUv\":" + lifecycle.HasStableUv.ToString().ToLowerInvariant()
            + "}"
            + "," + regionSnapshotJson
            + ",\"capabilities\":" + BuildCapabilitiesJson()
            + ",\"privacy\":{"
            + "\"rawCameraFrameStored\":false"
            + ",\"offDeviceUpload\":false"
            + "}"
            + "}";
    }

    private static string BuildUnavailableRegionSnapshotJsonFragment()
    {
        return "\"activeRegions\":[]"
            + ",\"appliedTextureSamples\":[]"
            + ",\"activeRegionSummary\":\"none\""
            + ",\"appliedTextureSampleSummary\":\"none\""
            + ",\"regions\":{"
            + "\"lip\":{\"available\":false,\"maskSource\":\"smooth_region_mask\",\"qaStatus\":\"unavailable\"}"
            + ",\"cheek\":{\"available\":false,\"maskSource\":\"smooth_region_mask\",\"qaStatus\":\"unavailable\"}"
            + ",\"eye\":{\"available\":false,\"maskSource\":\"smooth_region_mask\",\"qaStatus\":\"unavailable\"}"
            + "}";
    }

    private string BuildCapabilitiesJson()
    {
        XRFaceSubsystem faceSubsystem = null;
        XRGeneralSettings generalSettings = XRGeneralSettings.Instance;
        XRManagerSettings managerSettings = generalSettings != null ? generalSettings.Manager : null;

        if (managerSettings != null && managerSettings.activeLoader != null)
        {
            faceSubsystem = managerSettings.activeLoader.GetLoadedSubsystem<XRFaceSubsystem>();
        }

        XRFaceSubsystemDescriptor descriptor = faceSubsystem != null ? faceSubsystem.subsystemDescriptor : null;

        return "{"
            + "\"facePoseAvailable\":" + ReadBoolPropertyAsJsonBoolean(descriptor, "supportsFacePose")
            + ",\"meshVerticesAndIndicesAvailable\":" + ReadBoolPropertyAsJsonBoolean(descriptor, "supportsFaceMeshVerticesAndIndices")
            + ",\"meshUvAvailable\":" + ReadBoolPropertyAsJsonBoolean(descriptor, "supportsFaceMeshUVs")
            + ",\"eyePoseAvailable\":" + ReadBoolPropertyAsJsonBoolean(descriptor, "supportsEyeTracking")
            + ",\"blendShapesAvailable\":false"
            + ",\"providerSnapshot\":\"" + EscapeJsonString(faceSupportState) + "\""
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

    private string GetCurrentCameraFacing()
    {
        if (cameraManager == null)
        {
            return "unknown";
        }

        return cameraManager.currentFacingDirection.ToString();
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

    private static int GetFaceVertexCount(ARFace face)
    {
        return face != null && face.vertices.IsCreated ? face.vertices.Length : 0;
    }

    private static int GetFaceIndexCount(ARFace face)
    {
        return face != null && face.indices.IsCreated ? face.indices.Length : 0;
    }

    private static int GetFaceUvCount(ARFace face)
    {
        return face != null && face.uvs.IsCreated ? face.uvs.Length : 0;
    }

    private static int GetUnityMeshVertexCount(ARFace face)
    {
        if (face == null)
        {
            return 0;
        }

        MeshFilter meshFilter = face.GetComponent<MeshFilter>();
        Mesh mesh = meshFilter != null ? meshFilter.sharedMesh : null;
        return mesh != null ? mesh.vertexCount : 0;
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

    private static string FormatVector3Json(Vector3 value)
    {
        return "["
            + value.x.ToString("0.######", CultureInfo.InvariantCulture)
            + ","
            + value.y.ToString("0.######", CultureInfo.InvariantCulture)
            + ","
            + value.z.ToString("0.######", CultureInfo.InvariantCulture)
            + "]";
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

    private static string ReadBoolPropertyAsJsonBoolean(object target, string propertyName)
    {
        if (target == null)
        {
            return "false";
        }

        PropertyInfo property = target.GetType().GetProperty(propertyName, BindingFlags.Public | BindingFlags.Instance);
        if (property == null || property.PropertyType != typeof(bool))
        {
            return "false";
        }

        return ((bool)property.GetValue(target)).ToString().ToLowerInvariant();
    }
}
