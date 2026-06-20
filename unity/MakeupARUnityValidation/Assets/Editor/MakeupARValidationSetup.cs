#if UNITY_EDITOR
using System.IO;
using Unity.XR.CoreUtils;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEditor.XR.ARKit;
using UnityEditor.XR.Management;
using UnityEditor.XR.Management.Metadata;
using UnityEngine;
using UnityEngine.SceneManagement;
using UnityEngine.XR.ARFoundation;
using UnityEngine.XR.Management;
using UnityEngine.Rendering;

public static class MakeupARValidationSetup
{
    private const string ScenePath = "Assets/Scenes/MakeupARFaceValidation.unity";
    private const string FacePrefabPath = "Assets/Prefabs/ValidationFaceOverlay.prefab";
    private const string FaceMaterialPath = "Assets/Materials/ValidationFaceOverlay.mat";
    private const string XRSettingsFolder = "Assets/XR";
    private const string XRGeneralSettingsPath = XRSettingsFolder + "/XRGeneralSettingsPerBuildTarget.asset";
    private const string ARKitSettingsPath = XRSettingsFolder + "/ARKitSettings.asset";

    [MenuItem("Makeup AR Validation/Configure Project And Scene")]
    public static void ConfigureProjectAndScene()
    {
        EditorUserBuildSettings.SwitchActiveBuildTarget(BuildTargetGroup.iOS, BuildTarget.iOS);

        PlayerSettings.companyName = "MakeupAR";
        PlayerSettings.productName = "MakeupARUnityValidation";
        PlayerSettings.SetApplicationIdentifier(BuildTargetGroup.iOS, "com.makeupar.validation");
        PlayerSettings.iOS.cameraUsageDescription = "Camera access is required for AR face tracking validation.";
        PlayerSettings.iOS.targetOSVersionString = "15.0";

        EnsureFolders();
        EnableArKitLoaderForIos();
        ConfigureArKitFaceTracking();

        Material faceMaterial = CreateFaceOverlayMaterial();
        GameObject facePrefab = CreateFacePrefab(faceMaterial);
        CreateValidationScene(facePrefab, faceMaterial);

        AssetDatabase.SaveAssets();
        AssetDatabase.Refresh();
        Debug.Log("[M1] Unity AR Foundation validation project and scene configured.");
    }

    [MenuItem("Makeup AR Validation/Export iOS Project")]
    public static void ExportIosProject()
    {
        ConfigureProjectAndScene();

        string exportPath = Path.GetFullPath(Path.Combine(Application.dataPath, "../../..", "unity-builds", "ios-export"));
        Directory.CreateDirectory(exportPath);

        BuildPlayerOptions options = new BuildPlayerOptions
        {
            scenes = new[] { ScenePath },
            locationPathName = exportPath,
            target = BuildTarget.iOS,
            options = BuildOptions.None
        };

        UnityEditor.Build.Reporting.BuildReport report = BuildPipeline.BuildPlayer(options);
        Debug.Log("[M1] Unity iOS export result: " + report.summary.result + " at " + exportPath);
    }

    private static void EnsureFolders()
    {
        Directory.CreateDirectory("Assets/Scenes");
        Directory.CreateDirectory("Assets/Prefabs");
        Directory.CreateDirectory("Assets/Materials");
        Directory.CreateDirectory(XRSettingsFolder);
    }

    private static Material CreateFaceOverlayMaterial()
    {
        Shader shader = Shader.Find("Universal Render Pipeline/Unlit");
        if (shader == null)
        {
            shader = Shader.Find("Unlit/Color");
        }

        if (shader == null)
        {
            shader = Shader.Find("Standard");
        }

        Material material = AssetDatabase.LoadAssetAtPath<Material>(FaceMaterialPath);
        if (material == null)
        {
            material = new Material(shader);
            AssetDatabase.CreateAsset(material, FaceMaterialPath);
        }
        else
        {
            material.shader = shader;
        }

        ConfigureTransparentMaterial(material, new Color(1.0f, 0.05f, 0.85f, 0.65f));
        EditorUtility.SetDirty(material);
        return material;
    }

    private static void ConfigureTransparentMaterial(Material material, Color color)
    {
        material.color = color;
        if (material.HasProperty("_BaseColor"))
        {
            material.SetColor("_BaseColor", color);
        }

        if (material.HasProperty("_Color"))
        {
            material.SetColor("_Color", color);
        }

        if (material.HasProperty("_Surface"))
        {
            material.SetFloat("_Surface", 1.0f);
        }

        material.SetInt("_SrcBlend", (int)UnityEngine.Rendering.BlendMode.SrcAlpha);
        material.SetInt("_DstBlend", (int)UnityEngine.Rendering.BlendMode.OneMinusSrcAlpha);
        material.SetInt("_ZWrite", 0);
        material.DisableKeyword("_ALPHATEST_ON");
        material.EnableKeyword("_ALPHABLEND_ON");
        material.DisableKeyword("_ALPHAPREMULTIPLY_ON");
        material.renderQueue = (int)UnityEngine.Rendering.RenderQueue.Transparent;
    }

    private static GameObject CreateFacePrefab(Material faceMaterial)
    {
        bool loadedExistingPrefab = AssetDatabase.LoadAssetAtPath<GameObject>(FacePrefabPath) != null;
        GameObject prefabRoot = loadedExistingPrefab
            ? PrefabUtility.LoadPrefabContents(FacePrefabPath)
            : new GameObject("ValidationFaceOverlay");

        GetOrAddComponent<ARFace>(prefabRoot);
        GetOrAddComponent<MeshFilter>(prefabRoot);

        MeshRenderer renderer = GetOrAddComponent<MeshRenderer>(prefabRoot);
        renderer.sharedMaterial = faceMaterial;
        renderer.shadowCastingMode = ShadowCastingMode.Off;
        renderer.receiveShadows = false;
        renderer.allowOcclusionWhenDynamic = false;

        GetOrAddComponent<ARFaceMeshVisualizer>(prefabRoot);
        GetOrAddComponent<FaceTrackingMarker>(prefabRoot);

        GameObject prefab = PrefabUtility.SaveAsPrefabAsset(prefabRoot, FacePrefabPath);

        if (loadedExistingPrefab)
        {
            PrefabUtility.UnloadPrefabContents(prefabRoot);
        }
        else
        {
            Object.DestroyImmediate(prefabRoot);
        }

        return prefab;
    }

    private static T GetOrAddComponent<T>(GameObject gameObject) where T : Component
    {
        T component = gameObject.GetComponent<T>();
        if (component == null)
        {
            component = gameObject.AddComponent<T>();
        }

        return component;
    }

    private static void CreateValidationScene(GameObject facePrefab, Material faceMaterial)
    {
        Scene scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);

        GameObject arSessionObject = new GameObject("AR Session");
        arSessionObject.AddComponent<ARSession>();
        arSessionObject.AddComponent<ARInputManager>();

        GameObject xrOriginObject = new GameObject("XR Origin");
        XROrigin xrOrigin = xrOriginObject.AddComponent<XROrigin>();

        GameObject cameraOffsetObject = new GameObject("Camera Offset");
        cameraOffsetObject.transform.SetParent(xrOriginObject.transform, false);
        xrOrigin.CameraFloorOffsetObject = cameraOffsetObject;

        GameObject cameraObject = new GameObject("AR Camera");
        cameraObject.transform.SetParent(cameraOffsetObject.transform, false);
        cameraObject.tag = "MainCamera";

        Camera camera = cameraObject.AddComponent<Camera>();
        camera.clearFlags = CameraClearFlags.SolidColor;
        camera.backgroundColor = Color.black;
        camera.nearClipPlane = 0.1f;
        camera.farClipPlane = 20.0f;
        cameraObject.AddComponent<AudioListener>();
        ARCameraManager cameraManager = cameraObject.AddComponent<ARCameraManager>();
        cameraManager.requestedFacingDirection = CameraFacingDirection.User;
        cameraObject.AddComponent<ARCameraBackground>();
        xrOrigin.Camera = camera;

        ARFaceManager faceManager = xrOriginObject.AddComponent<ARFaceManager>();
        faceManager.facePrefab = facePrefab;
        faceManager.requestedMaximumFaceCount = 1;

        GameObject statusObject = new GameObject("RNBridge");
        FaceTrackingStatusReporter reporter = statusObject.AddComponent<FaceTrackingStatusReporter>();
        SerializedObject serializedReporter = new SerializedObject(reporter);
        serializedReporter.FindProperty("arSession").objectReferenceValue = arSessionObject.GetComponent<ARSession>();
        serializedReporter.FindProperty("cameraManager").objectReferenceValue = cameraManager;
        serializedReporter.FindProperty("faceManager").objectReferenceValue = faceManager;
        serializedReporter.FindProperty("drawDebugOverlay").boolValue = true;
        serializedReporter.ApplyModifiedPropertiesWithoutUndo();

        RNBridge bridge = statusObject.AddComponent<RNBridge>();
        SerializedObject serializedBridge = new SerializedObject(bridge);
        serializedBridge.FindProperty("faceManager").objectReferenceValue = faceManager;
        serializedBridge.FindProperty("overlayMaterial").objectReferenceValue = faceMaterial;
        serializedBridge.ApplyModifiedPropertiesWithoutUndo();

        GameObject lightObject = new GameObject("Directional Light");
        Light light = lightObject.AddComponent<Light>();
        light.type = LightType.Directional;
        light.intensity = 1.0f;
        lightObject.transform.rotation = Quaternion.Euler(50.0f, -30.0f, 0.0f);

        EditorSceneManager.SaveScene(scene, ScenePath);
        EditorBuildSettings.scenes = new[] { new EditorBuildSettingsScene(ScenePath, true) };
    }

    private static void EnableArKitLoaderForIos()
    {
        const string settingsKey = "Unity.XR.Management.XRGeneralSettingsPerBuildTarget";

        if (!EditorBuildSettings.TryGetConfigObject(settingsKey, out XRGeneralSettingsPerBuildTarget settingsPerBuildTarget))
        {
            settingsPerBuildTarget = AssetDatabase.LoadAssetAtPath<XRGeneralSettingsPerBuildTarget>(XRGeneralSettingsPath);
            if (settingsPerBuildTarget == null)
            {
                settingsPerBuildTarget = ScriptableObject.CreateInstance<XRGeneralSettingsPerBuildTarget>();
                AssetDatabase.CreateAsset(settingsPerBuildTarget, XRGeneralSettingsPath);
                AssetDatabase.SaveAssets();
            }

            EditorBuildSettings.AddConfigObject(settingsKey, settingsPerBuildTarget, true);
        }

        XRGeneralSettings generalSettings = settingsPerBuildTarget.SettingsForBuildTarget(BuildTargetGroup.iOS);
        if (generalSettings == null)
        {
            generalSettings = ScriptableObject.CreateInstance<XRGeneralSettings>();
            generalSettings.name = "iOS XR General Settings";
            AssetDatabase.AddObjectToAsset(generalSettings, settingsPerBuildTarget);
            settingsPerBuildTarget.SetSettingsForBuildTarget(BuildTargetGroup.iOS, generalSettings);
        }

        XRManagerSettings managerSettings = generalSettings.AssignedSettings;
        if (managerSettings == null)
        {
            managerSettings = ScriptableObject.CreateInstance<XRManagerSettings>();
            managerSettings.name = "iOS XR Manager Settings";
            AssetDatabase.AddObjectToAsset(managerSettings, settingsPerBuildTarget);
            generalSettings.AssignedSettings = managerSettings;
        }

        bool assigned = XRPackageMetadataStore.AssignLoader(managerSettings, "UnityEngine.XR.ARKit.ARKitLoader", BuildTargetGroup.iOS);
        if (!assigned)
        {
            Debug.LogWarning("[M1] ARKit loader was not assigned automatically. Confirm XR Plug-in Management > iOS > ARKit in the Unity UI.");
        }

        EditorUtility.SetDirty(settingsPerBuildTarget);
        EditorUtility.SetDirty(generalSettings);
        EditorUtility.SetDirty(managerSettings);
        AssetDatabase.SaveAssets();
    }

    private static void ConfigureArKitFaceTracking()
    {
        ARKitSettings settings = ARKitSettings.currentSettings;
        if (settings == null)
        {
            settings = AssetDatabase.LoadAssetAtPath<ARKitSettings>(ARKitSettingsPath);
        }

        if (settings == null)
        {
            settings = ScriptableObject.CreateInstance<ARKitSettings>();
            AssetDatabase.CreateAsset(settings, ARKitSettingsPath);
            AssetDatabase.SaveAssets();
        }

        settings.requirement = ARKitSettings.Requirement.Required;
        settings.faceTracking = true;
        ARKitSettings.currentSettings = settings;
        EditorUtility.SetDirty(settings);
        AssetDatabase.SaveAssets();
    }
}
#endif
