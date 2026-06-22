using UnityEditor;

public sealed class E7ReferenceAtlasTextureImporter : AssetPostprocessor
{
    private const string ReferenceAtlasPath =
        "Assets/Resources/E7ReferenceAtlas/e7ref-fastgate-20260622T160307Z-v0/";

    private void OnPreprocessTexture()
    {
        if (!assetPath.StartsWith(ReferenceAtlasPath, System.StringComparison.Ordinal)
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
