Shader "MakeupAR/EyebrowRegionMask"
{
    Properties
    {
        _MaskTex ("Eyebrow Strand Atlas", 2D) = "white" {}
        _BoundaryTex ("Eyebrow Boundary Mask", 2D) = "black" {}
        _RegionColor ("Brow Color", Color) = (0.22, 0.16, 0.13, 1)
        _NeutralizerColor ("Neutralizer Color", Color) = (0.78, 0.62, 0.52, 1)
        _Opacity ("Opacity", Range(0, 1)) = 0.75
        _Coverage ("Coverage", Range(0, 1)) = 0.9
        _Threshold ("Threshold", Range(0, 1)) = 0.02
        _Feather ("Feather", Range(0, 1)) = 0.34
        _VisibilityAlpha ("Visibility Alpha", Range(0, 1)) = 1
        _NeutralizerStrength ("Neutralizer Strength", Range(0, 1)) = 0.16
        _ToneLiftStrength ("Tone Lift Strength", Range(0, 1)) = 0.18
        _TintStrength ("Tint Strength", Range(0, 1)) = 0.72
        _StrandStrength ("Strand Strength", Range(0, 1.5)) = 1.0
        _RuntimeBoundaryMode ("Runtime Boundary Mode", Range(0, 1)) = 0
        _BrowShapeMode ("Brow Shape Mode", Range(0, 2)) = 0
    }

    SubShader
    {
        Tags
        {
            "Queue" = "Transparent+20"
            "RenderType" = "Transparent"
            "IgnoreProjector" = "True"
        }

        Cull Off
        ZWrite Off
        ZTest Always

        CGINCLUDE
        #include "UnityCG.cginc"

        sampler2D _MaskTex;
        sampler2D _BoundaryTex;
        float4 _MaskTex_TexelSize;
        float4 _BoundaryTex_TexelSize;
        fixed4 _RegionColor;
        fixed4 _NeutralizerColor;
        float _Opacity;
        float _Coverage;
        float _Threshold;
        float _Feather;
        float _VisibilityAlpha;
        float _NeutralizerStrength;
        float _ToneLiftStrength;
        float _TintStrength;
        float _StrandStrength;
        float _RuntimeBoundaryMode;
        float _BrowShapeMode;

        struct appdata
        {
            float4 vertex : POSITION;
            float2 uv : TEXCOORD0;
            float2 uv2 : TEXCOORD1;
        };

        struct v2f
        {
            float4 pos : SV_POSITION;
            float2 boundaryUv : TEXCOORD0;
            float2 localUv : TEXCOORD1;
        };

        v2f vert(appdata input)
        {
            v2f output;
            output.pos = UnityObjectToClipPos(input.vertex);
            output.boundaryUv = input.uv;
            output.localUv = input.uv2;
            return output;
        }

        float4 SampleSoft(sampler2D source, float4 texelSize, float2 uv)
        {
            float2 radius = texelSize.xy * lerp(0.75, 2.75, saturate(_Feather));
            float4 sample = tex2D(source, uv) * 0.34;
            sample += tex2D(source, uv + float2(radius.x, 0.0)) * 0.11;
            sample += tex2D(source, uv - float2(radius.x, 0.0)) * 0.11;
            sample += tex2D(source, uv + float2(0.0, radius.y)) * 0.11;
            sample += tex2D(source, uv - float2(0.0, radius.y)) * 0.11;
            sample += tex2D(source, uv + radius) * 0.055;
            sample += tex2D(source, uv - radius) * 0.055;
            sample += tex2D(source, uv + float2(radius.x, -radius.y)) * 0.055;
            sample += tex2D(source, uv + float2(-radius.x, radius.y)) * 0.055;
            return sample;
        }

        float4 BoundarySample(float2 uv)
        {
            return SampleSoft(_BoundaryTex, _BoundaryTex_TexelSize, saturate(uv));
        }

        float BoundaryCoverageFromSample(float4 boundary)
        {
            float hard = boundary.r;
            float soft = boundary.g;
            float edgeWidth = max(0.002, _Feather * 0.18);
            return saturate(max(smoothstep(_Threshold, _Threshold + edgeWidth, hard), soft * 0.92));
        }

        float BoundaryCoverage(float2 uv)
        {
            return BoundaryCoverageFromSample(BoundarySample(uv));
        }

        float BrowEndTaper(float localX)
        {
            float headTaper = lerp(0.34, 1.0, smoothstep(0.00, 0.20, localX));
            float tailTaper = lerp(1.0, 0.38, smoothstep(0.64, 1.0, localX));
            return saturate(headTaper * tailTaper);
        }

        float BrowShapeDensity(float localX)
        {
            float semiMode = 1.0 - saturate(abs(_BrowShapeMode - 0.0));
            float straightMode = 1.0 - saturate(abs(_BrowShapeMode - 1.0));
            float archMode = 1.0 - saturate(abs(_BrowShapeMode - 2.0));
            float archCenter = semiMode * 0.64 + straightMode * 0.64 + archMode * 0.64;
            float archStrength = semiMode * 0.18 + straightMode * 0.05 + archMode * 0.32;
            float headSoft = (1.0 - smoothstep(0.00, 0.24, localX)) * 0.20;
            float body = smoothstep(0.05, 0.34, localX)
                * (1.0 - smoothstep(0.64, 1.0, localX))
                * 0.78;
            float arch = (1.0 - smoothstep(0.00, 0.24, abs(localX - archCenter))) * archStrength;
            float tailFade = (1.0 - smoothstep(0.64, 1.0, localX)) * 0.16;
            return saturate(headSoft + body + arch + tailFade);
        }

        float OuterCleanupCoverage(float4 boundary)
        {
            float hard = saturate(boundary.r * 1.12);
            float cleanup = max(boundary.b, boundary.a);
            float atlasCleanup = saturate(cleanup - hard * 0.78);
            float runtimeCleanup = saturate(cleanup * (1.0 - hard * 0.62) * 0.74);
            return lerp(atlasCleanup, runtimeCleanup, step(0.5, _RuntimeBoundaryMode));
        }

        void ComputeBrowLocal(float2 uv, out float localX, out float localY, out float leftSide)
        {
            leftSide = 1.0 - step(0.5, uv.x);
            float leftLocalX = uv.x * 2.0;
            float rightLocalX = (uv.x - 0.5) * 2.0;
            localX = saturate(lerp(rightLocalX, leftLocalX, leftSide));
            localY = saturate(uv.y);
        }

        float2 BrowSourceUv(float localX, float localY, float leftSide)
        {
            float sourceY = lerp(0.350, 0.475, localY);
            float sourceLeftX = lerp(0.430, 0.075, localX);
            float sourceRightX = lerp(0.570, 0.925, localX);
            return float2(lerp(sourceRightX, sourceLeftX, leftSide), sourceY);
        }

        float4 SampleEyebrowSource(float2 sourceUv)
        {
            return SampleSoft(_MaskTex, _MaskTex_TexelSize, saturate(sourceUv));
        }

        float SourceDensity(float2 sourceUv)
        {
            float4 source = SampleEyebrowSource(sourceUv);
            float coverage = source.r * 1.25;
            float strand = source.g * 3.80;
            float fill = source.b * 5.20;
            float neutral = source.a * 2.45;
            return saturate(max(max(coverage, strand), max(fill, neutral)));
        }
        ENDCG

        Pass
        {
            Name "OuterSkinCleanup"
            Blend SrcAlpha OneMinusSrcAlpha

            CGPROGRAM
            #pragma vertex vert
            #pragma fragment frag

            fixed4 frag(v2f input) : SV_Target
            {
                float4 boundary = BoundarySample(input.boundaryUv);
                float cleanup = OuterCleanupCoverage(boundary);
                float alpha = saturate(
                    cleanup
                    * _NeutralizerStrength
                    * _Opacity
                    * _VisibilityAlpha
                    * _Coverage);
                return fixed4(_NeutralizerColor.rgb, alpha);
            }
            ENDCG
        }

        Pass
        {
            Name "BoundaryToneLift"
            Blend SrcAlpha OneMinusSrcAlpha

            CGPROGRAM
            #pragma vertex vert
            #pragma fragment frag

            fixed4 frag(v2f input) : SV_Target
            {
                float localX;
                float localY;
                float leftSide;
                ComputeBrowLocal(input.localUv, localX, localY, leftSide);
                float coverage = BoundaryCoverage(input.boundaryUv) * BrowEndTaper(localX);
                float shapeDensity = BrowShapeDensity(localX);
                float lift = saturate(coverage * (0.12 + shapeDensity * 0.22));
                float alpha = saturate(
                    lift
                    * _ToneLiftStrength
                    * _Opacity
                    * _VisibilityAlpha
                    * _Coverage);
                float3 liftColor = lerp(_NeutralizerColor.rgb, _RegionColor.rgb, 0.22);
                return fixed4(liftColor, alpha);
            }
            ENDCG
        }

        Pass
        {
            Name "BoundaryTintFill"
            Blend SrcAlpha OneMinusSrcAlpha

            CGPROGRAM
            #pragma vertex vert
            #pragma fragment frag

            fixed4 frag(v2f input) : SV_Target
            {
                float localX;
                float localY;
                float leftSide;
                ComputeBrowLocal(input.localUv, localX, localY, leftSide);
                float coverage = BoundaryCoverage(input.boundaryUv) * BrowEndTaper(localX);
                float source = SourceDensity(BrowSourceUv(localX, localY, leftSide));
                float shapeDensity = BrowShapeDensity(localX);
                float alpha = saturate(
                    coverage
                    * (0.220 + shapeDensity * 0.720 + source * 0.020)
                    * _TintStrength
                    * _Opacity
                    * _VisibilityAlpha
                    * _Coverage);
                return fixed4(_RegionColor.rgb, alpha);
            }
            ENDCG
        }

        Pass
        {
            Name "BoundaryStrandMultiply"
            Blend DstColor Zero

            CGPROGRAM
            #pragma vertex vert
            #pragma fragment frag

            fixed4 frag(v2f input) : SV_Target
            {
                float localX;
                float localY;
                float leftSide;
                ComputeBrowLocal(input.localUv, localX, localY, leftSide);
                float endTaper = BrowEndTaper(localX);
                float coverage = BoundaryCoverage(input.boundaryUv) * endTaper;
                float source = SourceDensity(BrowSourceUv(localX, localY, leftSide));

                float shapeDensity = BrowShapeDensity(localX);
                float softFill = saturate(coverage * (0.030 + source * 0.120 + shapeDensity * 0.035) * _TintStrength);
                float strands = saturate(BoundaryCoverage(input.boundaryUv) * sqrt(endTaper) * source * _StrandStrength);
                float strength = saturate((softFill * 0.35 + strands * 0.72) * _Opacity * _VisibilityAlpha * _Coverage);
                float3 darkBrow = saturate(lerp(_RegionColor.rgb, float3(0.06, 0.045, 0.038), 0.10));
                float3 multiplyFilter = lerp(float3(1.0, 1.0, 1.0), darkBrow, strength);
                return fixed4(multiplyFilter, 1.0);
            }
            ENDCG
        }
    }
}
