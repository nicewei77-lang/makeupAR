using System.Collections.Generic;
using System.Globalization;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.XR.ARFoundation;
using UnityEngine.XR.ARSubsystems;

public sealed class E3RegionMaskOverlay : MonoBehaviour
{
    public struct RegionApplyResult
    {
        public string Region;
        public bool Applied;
        public int FaceCount;
        public int MeshTriangleCount;
        public bool UsedFallback;
        public string TextureSample;
        public string TextureMode;
        public float Intensity;
        public float Feather;
        public string BlendMode;
    }

    private sealed class RegionRecipeState
    {
        public string Region = string.Empty;
        public string ColorHex = "#D94B74";
        public Color Color = new Color(0.85f, 0.29f, 0.45f, 0.65f);
        public float Opacity = 0.65f;
        public bool Enabled = true;
        public string TextureSample = "matte_lip";
        public string TextureMode = "sample";
        public float Intensity = 1.0f;
        public float Feather = 0.0f;
        public string BlendMode = "normal";
    }

    private sealed class FaceOverlayState
    {
        public readonly Dictionary<string, RegionOverlayView> Regions =
            new Dictionary<string, RegionOverlayView>();
    }

    private sealed class RegionOverlayView
    {
        public GameObject Root;
        public Mesh Mesh;
        public MeshRenderer MeshRenderer;
        public readonly List<MeshRenderer> FallbackRenderers = new List<MeshRenderer>();
    }

    [SerializeField] private ARFaceManager faceManager;
    [SerializeField] private bool useMeshMasks = true;

    private readonly Dictionary<string, RegionRecipeState> recipes =
        new Dictionary<string, RegionRecipeState>();
    private readonly Dictionary<ARFace, FaceOverlayState> overlays =
        new Dictionary<ARFace, FaceOverlayState>();
    private readonly Dictionary<string, Texture2D> sampleTextures =
        new Dictionary<string, Texture2D>();

    public void Configure(ARFaceManager manager)
    {
        if (faceManager == null)
        {
            faceManager = manager;
        }
    }

    private void Update()
    {
        if (recipes.Count == 0)
        {
            return;
        }

        foreach (string region in recipes.Keys)
        {
            ApplyRegionToTrackedFaces(region, false);
        }
    }

    public RegionApplyResult ApplyRegionRecipe(
        string region,
        string colorHex,
        Color color,
        float opacity,
        bool enabled,
        string textureSample,
        string textureMode,
        float intensity,
        float feather,
        string blendMode)
    {
        region = NormalizeRegion(region);
        opacity = Mathf.Clamp01(opacity);
        textureSample = NormalizeTextureSample(region, textureSample);

        recipes[region] = new RegionRecipeState
        {
            Region = region,
            ColorHex = colorHex,
            Color = new Color(color.r, color.g, color.b, opacity),
            Opacity = opacity,
            Enabled = enabled,
            TextureSample = textureSample,
            TextureMode = string.IsNullOrWhiteSpace(textureMode) ? "sample" : textureMode,
            Intensity = intensity <= 0.0f ? 1.0f : Mathf.Clamp01(intensity),
            Feather = Mathf.Clamp01(feather),
            BlendMode = string.IsNullOrWhiteSpace(blendMode) ? "normal" : blendMode
        };

        return ApplyRegionToTrackedFaces(region, true);
    }

    private RegionApplyResult ApplyRegionToTrackedFaces(string region, bool emitLog)
    {
        RefreshSceneReferences();

        RegionApplyResult result = new RegionApplyResult
        {
            Region = region,
            Applied = false,
            FaceCount = 0,
            MeshTriangleCount = 0,
            UsedFallback = false,
            TextureSample = string.Empty,
            TextureMode = string.Empty,
            Intensity = 0.0f,
            Feather = 0.0f,
            BlendMode = string.Empty
        };

        if (!recipes.TryGetValue(region, out RegionRecipeState recipe))
        {
            return result;
        }

        result.TextureSample = recipe.TextureSample;
        result.TextureMode = recipe.TextureMode;
        result.Intensity = recipe.Intensity;
        result.Feather = recipe.Feather;
        result.BlendMode = recipe.BlendMode;

        if (faceManager == null)
        {
            if (emitLog)
            {
                Debug.LogWarning("[E3] applied_region_skipped region=" + region + " reason=faceManager_missing");
            }

            return result;
        }

        foreach (ARFace face in faceManager.trackables)
        {
            if (face == null)
            {
                continue;
            }

            bool faceUsable = face.trackingState == TrackingState.Tracking
                || face.trackingState == TrackingState.Limited;
            FaceOverlayState faceState = EnsureFaceOverlayState(face);
            RegionOverlayView view = EnsureRegionOverlayView(face.transform, faceState, region);
            ApplyRecipeAppearance(view, recipe);

            if (!faceUsable || !recipe.Enabled)
            {
                SetViewVisibility(view, false, false);
                continue;
            }

            result.FaceCount++;
            int triangleCount = 0;
            bool meshApplied = useMeshMasks
                && TryUpdateMeshMask(face, view, region, out triangleCount);
            result.MeshTriangleCount += triangleCount;

            if (meshApplied)
            {
                SetViewVisibility(view, true, false);
            }
            else
            {
                SetViewVisibility(view, false, true);
                result.UsedFallback = true;
            }

            result.Applied = true;
        }

        if (emitLog)
        {
            Debug.Log(
                "[E3] applied_region"
                + " region=" + region
                + " color=" + recipe.ColorHex
                + " opacity=" + recipe.Opacity.ToString("0.##", CultureInfo.InvariantCulture)
                + " enabled=" + recipe.Enabled.ToString().ToLowerInvariant()
                + " applied=" + result.Applied.ToString().ToLowerInvariant()
                + " faceCount=" + result.FaceCount.ToString(CultureInfo.InvariantCulture)
                + " meshTriangles=" + result.MeshTriangleCount.ToString(CultureInfo.InvariantCulture)
                + " usedFallback=" + result.UsedFallback.ToString().ToLowerInvariant());
            Debug.Log(
                "[E4] applied_texture"
                + " region=" + region
                + " appliedTexture=" + recipe.TextureSample
                + " textureMode=" + recipe.TextureMode
                + " intensity=" + recipe.Intensity.ToString("0.##", CultureInfo.InvariantCulture)
                + " feather=" + recipe.Feather.ToString("0.##", CultureInfo.InvariantCulture)
                + " blendMode=" + recipe.BlendMode
                + " applied=" + result.Applied.ToString().ToLowerInvariant()
                + " appliedRegion=" + result.Region
                + " faceCount=" + result.FaceCount.ToString(CultureInfo.InvariantCulture)
                + " meshTriangles=" + result.MeshTriangleCount.ToString(CultureInfo.InvariantCulture)
                + " usedFallback=" + result.UsedFallback.ToString().ToLowerInvariant());
        }

        return result;
    }

    private void RefreshSceneReferences()
    {
        if (faceManager == null)
        {
            faceManager = FindFirstObjectByType<ARFaceManager>();
        }
    }

    private FaceOverlayState EnsureFaceOverlayState(ARFace face)
    {
        if (overlays.TryGetValue(face, out FaceOverlayState state))
        {
            return state;
        }

        state = new FaceOverlayState();
        overlays[face] = state;
        return state;
    }

    private RegionOverlayView EnsureRegionOverlayView(
        Transform faceTransform,
        FaceOverlayState state,
        string region)
    {
        if (state.Regions.TryGetValue(region, out RegionOverlayView view))
        {
            return view;
        }

        view = CreateRegionOverlayView(faceTransform, region);
        state.Regions[region] = view;
        return view;
    }

    private RegionOverlayView CreateRegionOverlayView(Transform faceTransform, string region)
    {
        GameObject root = new GameObject("E3 Region " + region);
        root.transform.SetParent(faceTransform, false);
        root.transform.localPosition = Vector3.zero;
        root.transform.localRotation = Quaternion.identity;
        root.transform.localScale = Vector3.one;

        Mesh mesh = new Mesh
        {
            name = "E3 " + region + " mesh mask"
        };
        mesh.MarkDynamic();

        MeshFilter meshFilter = root.AddComponent<MeshFilter>();
        MeshRenderer meshRenderer = root.AddComponent<MeshRenderer>();
        meshFilter.sharedMesh = mesh;
        meshRenderer.sharedMaterial = CreateRegionMaterial(region, Color.clear);
        ConfigureRenderer(meshRenderer);

        RegionOverlayView view = new RegionOverlayView
        {
            Root = root,
            Mesh = mesh,
            MeshRenderer = meshRenderer
        };

        CreateFallbackGeometry(root.transform, region, meshRenderer.sharedMaterial, view);
        SetViewVisibility(view, false, false);
        return view;
    }

    private static void CreateFallbackGeometry(
        Transform root,
        string region,
        Material material,
        RegionOverlayView view)
    {
        switch (region)
        {
            case "lip":
                AddFallbackEllipse(root, "lip", new Vector3(0.0f, -0.035f, 0.075f), new Vector3(0.08f, 0.026f, 0.008f), material, view);
                break;
            case "cheek":
                AddFallbackEllipse(root, "cheek-left", new Vector3(-0.072f, -0.004f, 0.07f), new Vector3(0.045f, 0.036f, 0.008f), material, view);
                AddFallbackEllipse(root, "cheek-right", new Vector3(0.072f, -0.004f, 0.07f), new Vector3(0.045f, 0.036f, 0.008f), material, view);
                break;
            case "eye":
                AddFallbackEllipse(root, "eye-left", new Vector3(-0.038f, 0.042f, 0.076f), new Vector3(0.044f, 0.018f, 0.008f), material, view);
                AddFallbackEllipse(root, "eye-right", new Vector3(0.038f, 0.042f, 0.076f), new Vector3(0.044f, 0.018f, 0.008f), material, view);
                break;
        }
    }

    private static void AddFallbackEllipse(
        Transform root,
        string name,
        Vector3 localPosition,
        Vector3 localScale,
        Material material,
        RegionOverlayView view)
    {
        GameObject primitive = GameObject.CreatePrimitive(PrimitiveType.Sphere);
        primitive.name = "E3 " + name + " fallback";
        primitive.transform.SetParent(root, false);
        primitive.transform.localPosition = localPosition;
        primitive.transform.localRotation = Quaternion.identity;
        primitive.transform.localScale = localScale;

        Collider collider = primitive.GetComponent<Collider>();
        if (collider != null)
        {
            Destroy(collider);
        }

        MeshRenderer renderer = primitive.GetComponent<MeshRenderer>();
        if (renderer == null)
        {
            return;
        }

        renderer.sharedMaterial = material;
        ConfigureRenderer(renderer);
        view.FallbackRenderers.Add(renderer);
    }

    private static bool TryUpdateMeshMask(
        ARFace face,
        RegionOverlayView view,
        string region,
        out int triangleCount)
    {
        triangleCount = 0;

        if (!face.vertices.IsCreated || !face.indices.IsCreated || face.vertices.Length == 0 || face.indices.Length < 3)
        {
            view.Mesh.Clear();
            return false;
        }

        bool hasTextureCoordinates = face.uvs.IsCreated && face.uvs.Length == face.vertices.Length;
        List<Vector3> vertices = new List<Vector3>(256);
        List<Vector2> textureCoordinates = new List<Vector2>(256);
        List<int> triangles = new List<int>(384);
        Dictionary<int, int> remapped = new Dictionary<int, int>();

        for (int index = 0; index + 2 < face.indices.Length; index += 3)
        {
            int sourceA = face.indices[index];
            int sourceB = face.indices[index + 1];
            int sourceC = face.indices[index + 2];

            if (sourceA < 0 || sourceB < 0 || sourceC < 0
                || sourceA >= face.vertices.Length
                || sourceB >= face.vertices.Length
                || sourceC >= face.vertices.Length)
            {
                continue;
            }

            Vector3 a = face.vertices[sourceA];
            Vector3 b = face.vertices[sourceB];
            Vector3 c = face.vertices[sourceC];
            Vector3 centroid = (a + b + c) / 3.0f;

            if (!IsCentroidInRegion(region, centroid))
            {
                continue;
            }

            triangles.Add(GetOrAddVertex(
                sourceA,
                a,
                hasTextureCoordinates ? face.uvs[sourceA] : Vector2.zero,
                vertices,
                textureCoordinates,
                remapped));
            triangles.Add(GetOrAddVertex(
                sourceB,
                b,
                hasTextureCoordinates ? face.uvs[sourceB] : Vector2.zero,
                vertices,
                textureCoordinates,
                remapped));
            triangles.Add(GetOrAddVertex(
                sourceC,
                c,
                hasTextureCoordinates ? face.uvs[sourceC] : Vector2.zero,
                vertices,
                textureCoordinates,
                remapped));
        }

        triangleCount = triangles.Count / 3;
        if (triangleCount == 0)
        {
            view.Mesh.Clear();
            return false;
        }

        view.Mesh.Clear();
        view.Mesh.SetVertices(vertices);
        view.Mesh.SetUVs(0, textureCoordinates);
        view.Mesh.SetTriangles(triangles, 0);
        view.Mesh.RecalculateNormals();
        view.Mesh.RecalculateBounds();
        return true;
    }

    private static int GetOrAddVertex(
        int sourceIndex,
        Vector3 value,
        Vector2 textureCoordinate,
        List<Vector3> vertices,
        List<Vector2> textureCoordinates,
        Dictionary<int, int> remapped)
    {
        if (remapped.TryGetValue(sourceIndex, out int targetIndex))
        {
            return targetIndex;
        }

        targetIndex = vertices.Count;
        vertices.Add(value);
        textureCoordinates.Add(textureCoordinate);
        remapped[sourceIndex] = targetIndex;
        return targetIndex;
    }

    private static bool IsCentroidInRegion(string region, Vector3 point)
    {
        float absX = Mathf.Abs(point.x);

        switch (region)
        {
            case "lip":
                return absX <= 0.058f && point.y >= -0.06f && point.y <= -0.012f;
            case "cheek":
                return absX >= 0.052f && absX <= 0.13f && point.y >= -0.028f && point.y <= 0.028f;
            case "eye":
                return absX >= 0.018f && absX <= 0.09f && point.y >= 0.022f && point.y <= 0.075f;
            default:
                return false;
        }
    }

    private void ApplyRecipeAppearance(RegionOverlayView view, RegionRecipeState recipe)
    {
        Texture2D texture = GetOrCreateTextureSample(recipe.TextureSample, recipe.Feather);
        Color materialColor = BuildMaterialColor(recipe);

        ApplyMaterialAppearance(
            view.MeshRenderer.sharedMaterial,
            materialColor,
            texture,
            recipe.BlendMode);

        foreach (MeshRenderer renderer in view.FallbackRenderers)
        {
            ApplyMaterialAppearance(
                renderer.sharedMaterial,
                materialColor,
                texture,
                recipe.BlendMode);
        }
    }

    private static Color BuildMaterialColor(RegionRecipeState recipe)
    {
        float sampleAlphaScale = 1.0f;
        float brightnessScale = 1.0f;

        switch (recipe.TextureSample)
        {
            case "soft_blush":
                sampleAlphaScale = Mathf.Lerp(0.58f, 0.9f, recipe.Intensity);
                brightnessScale = 1.06f;
                break;
            case "shimmer_eye":
                sampleAlphaScale = Mathf.Lerp(0.72f, 1.0f, recipe.Intensity);
                brightnessScale = Mathf.Lerp(1.05f, 1.35f, recipe.Intensity);
                break;
            default:
                sampleAlphaScale = Mathf.Lerp(0.78f, 1.0f, recipe.Intensity);
                brightnessScale = 0.96f;
                break;
        }

        return new Color(
            Mathf.Clamp01(recipe.Color.r * brightnessScale),
            Mathf.Clamp01(recipe.Color.g * brightnessScale),
            Mathf.Clamp01(recipe.Color.b * brightnessScale),
            Mathf.Clamp01(recipe.Opacity * sampleAlphaScale));
    }

    private Texture2D GetOrCreateTextureSample(string textureSample, float feather)
    {
        string key = textureSample + ":" + Mathf.RoundToInt(Mathf.Clamp01(feather) * 100.0f).ToString(CultureInfo.InvariantCulture);
        if (sampleTextures.TryGetValue(key, out Texture2D cachedTexture))
        {
            return cachedTexture;
        }

        Texture2D texture = CreateTextureSample(textureSample, feather);
        sampleTextures[key] = texture;
        return texture;
    }

    private static Texture2D CreateTextureSample(string textureSample, float feather)
    {
        const int size = 64;
        Texture2D texture = new Texture2D(size, size, TextureFormat.RGBA32, false)
        {
            name = "E4 " + textureSample + " debug texture",
            wrapMode = TextureWrapMode.Repeat,
            filterMode = FilterMode.Bilinear
        };

        feather = Mathf.Clamp01(feather);

        for (int y = 0; y < size; y++)
        {
            for (int x = 0; x < size; x++)
            {
                texture.SetPixel(x, y, GetTextureSamplePixel(textureSample, x, y, size, feather));
            }
        }

        texture.Apply(false, true);
        return texture;
    }

    private static Color GetTextureSamplePixel(
        string textureSample,
        int x,
        int y,
        int size,
        float feather)
    {
        float u = (x + 0.5f) / size;
        float v = (y + 0.5f) / size;
        float distanceFromCenter = Vector2.Distance(new Vector2(u, v), new Vector2(0.5f, 0.5f));

        switch (textureSample)
        {
            case "soft_blush":
            {
                float softEdge = Mathf.Lerp(0.38f, 0.62f, feather);
                float alpha = Mathf.Clamp01(1.0f - distanceFromCenter / softEdge);
                float grain = 0.92f + 0.08f * Mathf.Sin((x * 0.43f) + (y * 0.31f));
                return new Color(grain, grain, grain, alpha);
            }
            case "shimmer_eye":
            {
                int hash = Mathf.Abs((x * 73856093) ^ (y * 19349663) ^ 0x5bd1e995);
                bool sparkle = hash % 17 == 0 || (x + y) % 23 == 0;
                float stripe = ((x + y) % 11) < 3 ? 0.18f : 0.0f;
                float value = sparkle ? 1.0f : 0.58f + stripe;
                float alpha = sparkle ? 1.0f : 0.62f;
                return new Color(value, Mathf.Clamp01(value * 0.92f + 0.08f), 1.0f, alpha);
            }
            default:
            {
                float stripe = (x % 10) < 2 ? 0.92f : 1.0f;
                float pore = ((x * 13 + y * 7) % 29) == 0 ? 0.95f : 1.0f;
                return new Color(stripe * pore, stripe * pore, stripe * pore, 1.0f);
            }
        }
    }

    private static void SetViewVisibility(RegionOverlayView view, bool showMesh, bool showFallback)
    {
        if (view.MeshRenderer != null)
        {
            view.MeshRenderer.enabled = showMesh;
        }

        foreach (MeshRenderer renderer in view.FallbackRenderers)
        {
            if (renderer != null)
            {
                renderer.enabled = showFallback;
            }
        }
    }

    private static Material CreateRegionMaterial(string region, Color color)
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

        Material material = new Material(shader)
        {
            name = "E3 " + region + " debug material"
        };
        ApplyMaterialColor(material, color);
        return material;
    }

    private static void ConfigureRenderer(MeshRenderer renderer)
    {
        renderer.shadowCastingMode = ShadowCastingMode.Off;
        renderer.receiveShadows = false;
        renderer.allowOcclusionWhenDynamic = false;
        renderer.sortingOrder = 120;
    }

    private static void ApplyMaterialColor(Material material, Color color)
    {
        if (material == null)
        {
            return;
        }

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

        if (material.HasProperty("_SrcBlend"))
        {
            material.SetInt("_SrcBlend", (int)BlendMode.SrcAlpha);
        }

        if (material.HasProperty("_DstBlend"))
        {
            material.SetInt("_DstBlend", (int)BlendMode.OneMinusSrcAlpha);
        }

        if (material.HasProperty("_ZWrite"))
        {
            material.SetInt("_ZWrite", 0);
        }

        if (material.HasProperty("_ZTest"))
        {
            material.SetInt("_ZTest", (int)CompareFunction.Always);
        }

        material.DisableKeyword("_ALPHATEST_ON");
        material.EnableKeyword("_ALPHABLEND_ON");
        material.DisableKeyword("_ALPHAPREMULTIPLY_ON");
        material.renderQueue = 5000;
    }

    private static void ApplyMaterialAppearance(
        Material material,
        Color color,
        Texture texture,
        string blendMode)
    {
        ApplyMaterialColor(material, color);

        if (texture != null)
        {
            if (material.HasProperty("_BaseMap"))
            {
                material.SetTexture("_BaseMap", texture);
            }

            if (material.HasProperty("_MainTex"))
            {
                material.SetTexture("_MainTex", texture);
            }
        }

        ApplyBlendMode(material, blendMode);
    }

    private static void ApplyBlendMode(Material material, string blendMode)
    {
        if (material == null)
        {
            return;
        }

        switch (string.IsNullOrWhiteSpace(blendMode) ? "normal" : blendMode.Trim().ToLowerInvariant())
        {
            case "multiply":
                if (material.HasProperty("_SrcBlend"))
                {
                    material.SetInt("_SrcBlend", (int)BlendMode.DstColor);
                }

                if (material.HasProperty("_DstBlend"))
                {
                    material.SetInt("_DstBlend", (int)BlendMode.OneMinusSrcAlpha);
                }
                break;
            case "screen":
                if (material.HasProperty("_SrcBlend"))
                {
                    material.SetInt("_SrcBlend", (int)BlendMode.OneMinusDstColor);
                }

                if (material.HasProperty("_DstBlend"))
                {
                    material.SetInt("_DstBlend", (int)BlendMode.One);
                }
                break;
            default:
                if (material.HasProperty("_SrcBlend"))
                {
                    material.SetInt("_SrcBlend", (int)BlendMode.SrcAlpha);
                }

                if (material.HasProperty("_DstBlend"))
                {
                    material.SetInt("_DstBlend", (int)BlendMode.OneMinusSrcAlpha);
                }
                break;
        }
    }

    private static string NormalizeRegion(string region)
    {
        region = string.IsNullOrWhiteSpace(region) ? string.Empty : region.Trim().ToLowerInvariant();
        if (region == "lip" || region == "cheek" || region == "eye")
        {
            return region;
        }

        return "lip";
    }

    private static string NormalizeTextureSample(string region, string textureSample)
    {
        textureSample = string.IsNullOrWhiteSpace(textureSample)
            ? string.Empty
            : textureSample.Trim().ToLowerInvariant();

        if ((region == "lip" && textureSample == "matte_lip")
            || (region == "cheek" && textureSample == "soft_blush")
            || (region == "eye" && textureSample == "shimmer_eye"))
        {
            return textureSample;
        }

        switch (region)
        {
            case "lip":
                return "matte_lip";
            case "cheek":
                return "soft_blush";
            case "eye":
                return "shimmer_eye";
            default:
                return "matte_lip";
        }
    }
}
