using UnityEditor;

public sealed class SmoothRegionMaskTextureImporter : AssetPostprocessor
{
    private const string SmoothMaskPath =
        "Assets/Resources/SmoothRegionMasks/";

    private void OnPreprocessTexture()
    {
        if (!assetPath.StartsWith(SmoothMaskPath, System.StringComparison.Ordinal)
            || !assetPath.EndsWith(".png", System.StringComparison.OrdinalIgnoreCase))
        {
            return;
        }

        TextureImporter importer = (TextureImporter)assetImporter;
        importer.textureType = TextureImporterType.Default;
        importer.sRGBTexture = false;
        importer.alphaSource = TextureImporterAlphaSource.FromInput;
        importer.isReadable = true;
        importer.mipmapEnabled = false;
        importer.wrapMode = UnityEngine.TextureWrapMode.Clamp;
        importer.filterMode = UnityEngine.FilterMode.Bilinear;
        importer.textureCompression = TextureImporterCompression.Uncompressed;
    }
}
