Shader "MakeupAR/SmoothRegionMask"
{
    Properties
    {
        _MaskTex ("Mask Texture", 2D) = "black" {}
        _RegionColor ("Region Color", Color) = (0.85, 0.29, 0.45, 1)
        _SecondaryColor ("Secondary Color", Color) = (0.95, 0.61, 0.67, 1)
        _Opacity ("Opacity", Range(0, 1)) = 0.65
        _Threshold ("Threshold", Range(0, 1)) = 0.04
        _Feather ("Feather", Range(0, 1)) = 0.5
        _VisibilityAlpha ("Visibility Alpha", Range(0, 1)) = 1
        _Coverage ("Coverage", Range(0, 1)) = 0.62
        _Roughness ("Roughness", Range(0, 1)) = 0.88
        _Specular ("Specular", Range(0, 1)) = 0.04
        _SpecularPower ("Specular Power", Range(1, 64)) = 8
        _GlossBoost ("Gloss Boost", Range(0, 1)) = 0
        _GradientAmount ("Gradient Amount", Range(0, 1)) = 0
        _PreserveDetail ("Preserve Detail", Range(0, 1)) = 1
        _LipStyleMode ("Lip Style Mode", Float) = -1
        [HideInInspector] _PigmentMultiply ("Pigment Multiply", Float) = 0
        [HideInInspector] _UseScreenSpaceMask ("Use Screen Space Mask", Float) = 0
        [HideInInspector] _SrcBlend ("Source Blend", Float) = 5
        [HideInInspector] _DstBlend ("Destination Blend", Float) = 10
    }

    SubShader
    {
        Tags
        {
            "Queue" = "Transparent"
            "RenderType" = "Transparent"
            "IgnoreProjector" = "True"
        }

        Pass
        {
            Name "PigmentMultiplyOrAlphaFallback"
            Tags { "LightMode" = "Always" }

            Blend [_SrcBlend] [_DstBlend]
            ZWrite Off
            ZTest Always
            Cull Off

            CGPROGRAM
            #pragma vertex vert
            #pragma fragment frag

            #include "UnityCG.cginc"

            sampler2D _MaskTex;
            float4 _MaskTex_TexelSize;
            float4 _RegionColor;
            float4 _SecondaryColor;
            float _Opacity;
            float _Threshold;
            float _Feather;
            float _VisibilityAlpha;
            float _Coverage;
            float _Roughness;
            float _Specular;
            float _SpecularPower;
            float _GlossBoost;
            float _GradientAmount;
            float _PreserveDetail;
            float _LipStyleMode;
            float _PigmentMultiply;
            float _UseScreenSpaceMask;

            struct appdata
            {
                float4 vertex : POSITION;
                float2 uv : TEXCOORD0;
            };

            struct v2f
            {
                float4 vertex : SV_POSITION;
                float2 uv : TEXCOORD0;
                float4 clipPos : TEXCOORD1;
            };

            v2f vert(appdata input)
            {
                v2f output;
                output.vertex = UnityObjectToClipPos(input.vertex);
                output.clipPos = output.vertex;
                output.uv = input.uv;
                return output;
            }

            float FeatherTexelRadius(float feather)
            {
                return lerp(1.25, 5.5, saturate(feather * 2.35));
            }

            float4 SampleMaskSoft(float2 uv)
            {
                float2 texel = _MaskTex_TexelSize.xy;
                float radius = FeatherTexelRadius(_Feather);
                float2 nearTexel = texel * radius;
                float2 farTexel = nearTexel * 1.85;
                float4 center = tex2D(_MaskTex, uv) * 0.24;
                float4 nearAxis = (
                    tex2D(_MaskTex, uv + float2(nearTexel.x, 0.0)) +
                    tex2D(_MaskTex, uv - float2(nearTexel.x, 0.0)) +
                    tex2D(_MaskTex, uv + float2(0.0, nearTexel.y)) +
                    tex2D(_MaskTex, uv - float2(0.0, nearTexel.y))) * 0.085;
                float4 nearDiagonal = (
                    tex2D(_MaskTex, uv + nearTexel) +
                    tex2D(_MaskTex, uv - nearTexel) +
                    tex2D(_MaskTex, uv + float2(nearTexel.x, -nearTexel.y)) +
                    tex2D(_MaskTex, uv + float2(-nearTexel.x, nearTexel.y))) * 0.045;
                float4 farAxis = (
                    tex2D(_MaskTex, uv + float2(farTexel.x, 0.0)) +
                    tex2D(_MaskTex, uv - float2(farTexel.x, 0.0)) +
                    tex2D(_MaskTex, uv + float2(0.0, farTexel.y)) +
                    tex2D(_MaskTex, uv - float2(0.0, farTexel.y))) * 0.06;
                return center + nearAxis + nearDiagonal + farAxis;
            }

            float SoftMaskAlpha(float value, float threshold, float feather)
            {
                float soft = max(feather, 0.00001);
                return smoothstep(saturate(threshold - soft * 0.46), saturate(threshold + soft), value);
            }

            float CoreMaskAlpha(float value, float threshold, float feather)
            {
                float soft = max(feather, 0.00001);
                return smoothstep(saturate(threshold + soft * 0.18), saturate(threshold + soft * 0.88), value);
            }

            float LipCenterDensity(float2 uv, float maskAlpha)
            {
                float2 lipUv = uv - float2(0.5, 0.5);
                float horizontal = 1.0 - smoothstep(0.05, 0.42, abs(lipUv.x));
                float mouthProximity = 1.0 - smoothstep(0.02, 0.18, abs(lipUv.y));
                float lowerCenter = 1.0 - smoothstep(0.025, 0.30, distance(lipUv, float2(0.0, -0.055)));
                return saturate(maskAlpha * max(horizontal * mouthProximity, lowerCenter * 0.68));
            }

            fixed4 frag(v2f input) : SV_Target
            {
                float2 maskUv = input.uv;
                if (_UseScreenSpaceMask > 0.5)
                {
                    float2 ndc = input.clipPos.xy / max(input.clipPos.w, 0.00001);
                    maskUv = saturate(ndc * 0.5 + 0.5);
                }

                float4 mask = tex2D(_MaskTex, maskUv);
                float4 softMask = SampleMaskSoft(maskUv);
                float fullSoft = SoftMaskAlpha(softMask.r, _Threshold, _Feather);
                float fullCore = CoreMaskAlpha(mask.r, _Threshold, _Feather);
                float overlineSoft = SoftMaskAlpha(softMask.g, _Threshold, _Feather);
                float gradientMask = SoftMaskAlpha(max(softMask.b, mask.b), _Threshold, _Feather);
                float edgeBand = saturate(fullSoft - fullCore);
                float centerDensity = LipCenterDensity(maskUv, fullSoft);
                float innerDensity = saturate(max(gradientMask, centerDensity) * fullCore);
                float coverage = saturate(max(_Coverage, 0.001));
                float baseStain = fullSoft * coverage * 0.54;
                float innerLayer = innerDensity * coverage * 0.32;
                float edgeLayer = edgeBand * coverage * 0.06;
                float maskStrength = baseStain + innerLayer + edgeLayer;
                float3 pigmentColor = saturate(_RegionColor.rgb);
                float3 alphaColor = pigmentColor;

                if (_LipStyleMode > -0.5)
                {
                    if (_LipStyleMode < 0.5)
                    {
                        maskStrength = saturate(baseStain * 1.02 + innerLayer * 0.48 + edgeLayer * 0.20);
                        pigmentColor = saturate(lerp(pigmentColor, pigmentColor * 0.82, saturate(_Roughness) * 0.28));
                        alphaColor = pigmentColor;
                    }
                    else if (_LipStyleMode < 1.5)
                    {
                        maskStrength = saturate(baseStain * 0.84 + innerLayer * 0.30 + edgeLayer * 0.16);
                        pigmentColor = saturate(lerp(pigmentColor, _SecondaryColor.rgb, 0.035));
                        alphaColor = pigmentColor;
                    }
                    else if (_LipStyleMode < 2.5)
                    {
                        maskStrength = saturate(baseStain * 0.98 + innerLayer * 0.34 + edgeLayer * 0.30 + overlineSoft * coverage * 0.08);
                        pigmentColor = saturate(lerp(pigmentColor, pigmentColor * 0.88, 0.12));
                        alphaColor = pigmentColor;
                    }
                    else if (_LipStyleMode < 3.5)
                    {
                        float gradientMix = saturate(_GradientAmount);
                        float outerSoftWash = fullSoft * coverage * lerp(0.26, 0.18, gradientMix);
                        float softEdgeFeather = edgeBand * coverage * 0.035;
                        float innerGradientTint = innerDensity * coverage * lerp(0.52, 0.86, gradientMix);
                        maskStrength = saturate(outerSoftWash + softEdgeFeather + innerGradientTint);
                        pigmentColor = saturate(lerp(_SecondaryColor.rgb, pigmentColor * 0.92, saturate(innerDensity * 1.25 + 0.08)));
                        alphaColor = pigmentColor;
                    }
                    else
                    {
                        float lineAlpha = saturate(overlineSoft - fullCore * 0.42);
                        maskStrength = max(baseStain * 0.54 + edgeLayer * 0.2, lineAlpha * coverage * 0.55);
                        pigmentColor = saturate(lerp(_SecondaryColor.rgb, pigmentColor, fullCore));
                        alphaColor = pigmentColor;
                    }
                }

                float preserveScale = lerp(1.0, 0.92, saturate(_PreserveDetail));
                float opacity = saturate(_Opacity * _VisibilityAlpha);

                if (_PigmentMultiply > 0.5)
                {
                    float styleCapBoost = _LipStyleMode < 0.5 ? 0.18 : (_LipStyleMode < 3.5 && _LipStyleMode >= 2.5 ? 0.14 : 0.0);
                    float maxPigmentStrength = saturate(lerp(0.42, 0.66, saturate(_Coverage)) + styleCapBoost);
                    float pigmentStrength = min(saturate(maskStrength * opacity * preserveScale), maxPigmentStrength);
                    float3 pigmentFilter = lerp(float3(1.0, 1.0, 1.0), pigmentColor, pigmentStrength);
                    return fixed4(saturate(pigmentFilter), 1.0);
                }

                float alpha = maskStrength * opacity * preserveScale;
                return fixed4(alphaColor, saturate(alpha));
            }
            ENDCG
        }

        Pass
        {
            Name "GlossAdditiveHighlight"
            Tags { "LightMode" = "Always" }

            Blend One One
            ZWrite Off
            ZTest Always
            Cull Off

            CGPROGRAM
            #pragma vertex vert
            #pragma fragment frag

            #include "UnityCG.cginc"

            sampler2D _MaskTex;
            float4 _MaskTex_TexelSize;
            float4 _RegionColor;
            float4 _SecondaryColor;
            float _Opacity;
            float _Threshold;
            float _Feather;
            float _VisibilityAlpha;
            float _Coverage;
            float _Specular;
            float _SpecularPower;
            float _GlossBoost;
            float _LipStyleMode;
            float _UseScreenSpaceMask;

            struct appdata
            {
                float4 vertex : POSITION;
                float2 uv : TEXCOORD0;
            };

            struct v2f
            {
                float4 vertex : SV_POSITION;
                float2 uv : TEXCOORD0;
                float4 clipPos : TEXCOORD1;
            };

            v2f vert(appdata input)
            {
                v2f output;
                output.vertex = UnityObjectToClipPos(input.vertex);
                output.clipPos = output.vertex;
                output.uv = input.uv;
                return output;
            }

            float FeatherTexelRadius(float feather)
            {
                return lerp(1.25, 5.5, saturate(feather * 2.35));
            }

            float4 SampleMaskSoft(float2 uv)
            {
                float2 texel = _MaskTex_TexelSize.xy;
                float radius = FeatherTexelRadius(_Feather);
                float2 nearTexel = texel * radius;
                float2 farTexel = nearTexel * 1.85;
                float4 center = tex2D(_MaskTex, uv) * 0.24;
                float4 nearAxis = (
                    tex2D(_MaskTex, uv + float2(nearTexel.x, 0.0)) +
                    tex2D(_MaskTex, uv - float2(nearTexel.x, 0.0)) +
                    tex2D(_MaskTex, uv + float2(0.0, nearTexel.y)) +
                    tex2D(_MaskTex, uv - float2(0.0, nearTexel.y))) * 0.085;
                float4 nearDiagonal = (
                    tex2D(_MaskTex, uv + nearTexel) +
                    tex2D(_MaskTex, uv - nearTexel) +
                    tex2D(_MaskTex, uv + float2(nearTexel.x, -nearTexel.y)) +
                    tex2D(_MaskTex, uv + float2(-nearTexel.x, nearTexel.y))) * 0.045;
                float4 farAxis = (
                    tex2D(_MaskTex, uv + float2(farTexel.x, 0.0)) +
                    tex2D(_MaskTex, uv - float2(farTexel.x, 0.0)) +
                    tex2D(_MaskTex, uv + float2(0.0, farTexel.y)) +
                    tex2D(_MaskTex, uv - float2(0.0, farTexel.y))) * 0.06;
                return center + nearAxis + nearDiagonal + farAxis;
            }

            float SoftMaskAlpha(float value, float threshold, float feather)
            {
                float soft = max(feather, 0.00001);
                return smoothstep(saturate(threshold - soft * 0.46), saturate(threshold + soft), value);
            }

            float CoreMaskAlpha(float value, float threshold, float feather)
            {
                float soft = max(feather, 0.00001);
                return smoothstep(saturate(threshold + soft * 0.18), saturate(threshold + soft * 0.88), value);
            }

            fixed4 frag(v2f input) : SV_Target
            {
                if (_LipStyleMode < 0.5 || _LipStyleMode >= 1.5)
                {
                    return fixed4(0.0, 0.0, 0.0, 0.0);
                }

                float2 maskUv = input.uv;
                if (_UseScreenSpaceMask > 0.5)
                {
                    float2 ndc = input.clipPos.xy / max(input.clipPos.w, 0.00001);
                    maskUv = saturate(ndc * 0.5 + 0.5);
                }

                float4 mask = tex2D(_MaskTex, maskUv);
                float4 softMask = SampleMaskSoft(maskUv);
                float fullSoft = SoftMaskAlpha(softMask.r, _Threshold, _Feather);
                float fullCore = CoreMaskAlpha(mask.r, _Threshold, _Feather);
                float coverage = saturate(max(_Coverage, 0.001));

                float glossMask = max(mask.a, softMask.a * 0.35);
                float lineFeather = max(_Feather * 0.20, 0.026);
                float thinHorizontalLine = SoftMaskAlpha(glossMask, max(_Threshold * 0.62, 0.018), lineFeather)
                    * fullSoft
                    * fullCore;
                float highlight = thinHorizontalLine
                    * coverage
                    * saturate(_Specular)
                    * saturate(_GlossBoost)
                    * saturate(_Opacity)
                    * saturate(_VisibilityAlpha)
                    * 0.46;
                float3 tintedWetColor = saturate(lerp(_RegionColor.rgb, _SecondaryColor.rgb, 0.38));
                float3 highlightColor = saturate(lerp(tintedWetColor, float3(1.0, 0.94, 0.92), 0.30));
                return fixed4(highlightColor * highlight, 0.0);
            }
            ENDCG
        }
    }
}
