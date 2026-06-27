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
        _GlossColor ("Gloss Color", Color) = (1.0, 0.78, 0.84, 1)
        _GlossSharpness ("Gloss Sharpness", Range(0, 1)) = 0.72
        _GlossHaloIntensity ("Gloss Halo Intensity", Range(0, 1)) = 0.07
        _GradientAmount ("Gradient Amount", Range(0, 1)) = 0
        _PreserveDetail ("Preserve Detail", Range(0, 1)) = 1
        _LipStyleMode ("Lip Style Mode", Float) = -1
        [HideInInspector] _CheekBlushMode ("Cheek Blush Mode", Float) = 0
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
            float4 _GlossColor;
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
            float _CheekBlushMode;
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

            float4 SampleMaskPowderSoft(float2 uv)
            {
                float2 texel = _MaskTex_TexelSize.xy;
                float radius = FeatherTexelRadius(_Feather);
                float2 nearTexel = texel * radius * 1.55;
                float2 midTexel = texel * radius * 3.05;
                float2 farTexel = texel * radius * 5.25;
                float4 center = tex2D(_MaskTex, uv) * 0.16;
                float4 nearAxis = (
                    tex2D(_MaskTex, uv + float2(nearTexel.x, 0.0)) +
                    tex2D(_MaskTex, uv - float2(nearTexel.x, 0.0)) +
                    tex2D(_MaskTex, uv + float2(0.0, nearTexel.y)) +
                    tex2D(_MaskTex, uv - float2(0.0, nearTexel.y))) * 0.0525;
                float4 nearDiagonal = (
                    tex2D(_MaskTex, uv + nearTexel) +
                    tex2D(_MaskTex, uv - nearTexel) +
                    tex2D(_MaskTex, uv + float2(nearTexel.x, -nearTexel.y)) +
                    tex2D(_MaskTex, uv + float2(-nearTexel.x, nearTexel.y))) * 0.035;
                float4 midAxis = (
                    tex2D(_MaskTex, uv + float2(midTexel.x, 0.0)) +
                    tex2D(_MaskTex, uv - float2(midTexel.x, 0.0)) +
                    tex2D(_MaskTex, uv + float2(0.0, midTexel.y)) +
                    tex2D(_MaskTex, uv - float2(0.0, midTexel.y))) * 0.055;
                float4 farAxis = (
                    tex2D(_MaskTex, uv + float2(farTexel.x, 0.0)) +
                    tex2D(_MaskTex, uv - float2(farTexel.x, 0.0)) +
                    tex2D(_MaskTex, uv + float2(0.0, farTexel.y)) +
                    tex2D(_MaskTex, uv - float2(0.0, farTexel.y))) * 0.0275;
                return saturate(center + nearAxis + nearDiagonal + midAxis + farAxis);
            }

            float GradientDensityBlur(float2 uv)
            {
                float2 texel = _MaskTex_TexelSize.xy;
                float radius = FeatherTexelRadius(_Feather) * 2.25;
                float2 nearTexel = texel * radius;
                float2 farTexel = nearTexel * 1.75;
                float center = tex2D(_MaskTex, uv).b * 0.16;
                float nearAxis = (
                    tex2D(_MaskTex, uv + float2(nearTexel.x, 0.0)).b +
                    tex2D(_MaskTex, uv - float2(nearTexel.x, 0.0)).b +
                    tex2D(_MaskTex, uv + float2(0.0, nearTexel.y)).b +
                    tex2D(_MaskTex, uv - float2(0.0, nearTexel.y)).b) * 0.075;
                float nearDiagonal = (
                    tex2D(_MaskTex, uv + nearTexel).b +
                    tex2D(_MaskTex, uv - nearTexel).b +
                    tex2D(_MaskTex, uv + float2(nearTexel.x, -nearTexel.y)).b +
                    tex2D(_MaskTex, uv + float2(-nearTexel.x, nearTexel.y)).b) * 0.045;
                float farAxis = (
                    tex2D(_MaskTex, uv + float2(farTexel.x, 0.0)).b +
                    tex2D(_MaskTex, uv - float2(farTexel.x, 0.0)).b +
                    tex2D(_MaskTex, uv + float2(0.0, farTexel.y)).b +
                    tex2D(_MaskTex, uv - float2(0.0, farTexel.y)).b) * 0.09;
                return saturate(center + nearAxis + nearDiagonal + farAxis);
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
                float legacyInnerDensity = saturate(max(gradientMask * fullCore, centerDensity * fullCore));
                float coverage = saturate(max(_Coverage, 0.001));
                float baseStain = fullSoft * coverage * 0.54;
                float innerLayer = legacyInnerDensity * coverage * 0.32;
                float edgeLayer = edgeBand * coverage * 0.06;
                float maskStrength = baseStain + innerLayer + edgeLayer;
                float3 pigmentColor = saturate(_RegionColor.rgb);
                float3 alphaColor = pigmentColor;
                float matteReferenceMaskStrength = saturate(baseStain * 1.02 + innerLayer * 0.48 + edgeLayer * 0.20);
                float3 matteReferencePigmentColor = saturate(lerp(
                    pigmentColor,
                    pigmentColor * 0.82,
                    0.28));

                if (_CheekBlushMode > 0.5)
                {
                    float4 cheekPowderMask = SampleMaskPowderSoft(maskUv);
                    float cheekAlphaRaw = max(mask.r, mask.a);
                    float cheekAlphaSeed = max(
                        max(softMask.r, softMask.a * 0.92),
                        max(cheekPowderMask.r, cheekPowderMask.a * 0.90));
                    float cheekSoft = SoftMaskAlpha(cheekAlphaSeed, _Threshold, _Feather);
                    float cheekBody = smoothstep(0.055, 0.48, max(cheekAlphaRaw, softMask.r * 0.82));
                    float cheekDensity = saturate(max(
                        mask.b * 0.50,
                        max(softMask.b * 0.48, GradientDensityBlur(maskUv) * 0.44)));
                    float cheekDensityGuide = smoothstep(0.06, 0.72, cheekDensity);
                    float cheekPowderStrength = saturate(
                        cheekSoft
                        * lerp(0.28, 1.0, cheekBody)
                        * lerp(0.82, 1.0, cheekDensityGuide));
                    float cheekCenterBoost = saturate(cheekBody * cheekDensityGuide) * 0.12;

                    maskStrength = saturate(
                        cheekPowderStrength * coverage * 0.92
                        + cheekCenterBoost * coverage);
                    float3 cheekBlushPigment = saturate(lerp(_RegionColor.rgb, _SecondaryColor.rgb, 0.14));
                    pigmentColor = cheekBlushPigment;
                    alphaColor = pigmentColor;
                }
                else if (_LipStyleMode > -0.5)
                {
                    if (_LipStyleMode < 0.5)
                    {
                        maskStrength = matteReferenceMaskStrength;
                        pigmentColor = matteReferencePigmentColor;
                        alphaColor = pigmentColor;
                    }
                    else if (_LipStyleMode < 1.5)
                    {
                        maskStrength = matteReferenceMaskStrength;
                        pigmentColor = matteReferencePigmentColor;
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
                        float gradientDensityRaw = max(mask.b, softMask.b * 0.82);
                        float gradientDensityBlurred = saturate(GradientDensityBlur(maskUv) * 1.45);
                        float gradientDensitySeed = saturate(lerp(
                            gradientDensityRaw,
                            gradientDensityBlurred,
                            lerp(0.42, 0.56, gradientMix)));
                        float gradientDensityRamp = pow(gradientDensitySeed, lerp(1.02, 0.78, gradientMix));
                        float singleGradientDensity = saturate(fullSoft * gradientDensityRamp);
                        float gradientDensityCurve = pow(singleGradientDensity, lerp(1.46, 1.24, gradientMix));
                        float gradientStrengthScale = lerp(0.72, 1.08, gradientDensityCurve);
                        float matteDerivedGradientStrength = saturate(
                            matteReferenceMaskStrength * gradientStrengthScale);
                        maskStrength = matteDerivedGradientStrength;
                        pigmentColor = matteReferencePigmentColor;
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
                    float styleCapBoost = _CheekBlushMode > 0.5
                        ? 0.0
                        : (_LipStyleMode < 0.5
                            ? 0.18
                            : (_LipStyleMode >= 0.5 && _LipStyleMode < 1.5
                                ? 0.10
                                : (_LipStyleMode < 3.5 && _LipStyleMode >= 2.5 ? 0.14 : 0.0)));
                    float maxPigmentStrength = _CheekBlushMode > 0.5
                        ? saturate(lerp(0.36, 0.57, saturate(_Coverage)))
                        : saturate(lerp(0.42, 0.66, saturate(_Coverage)) + styleCapBoost);
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
            float4 _GlossColor;
            float _Opacity;
            float _Threshold;
            float _Feather;
            float _VisibilityAlpha;
            float _Coverage;
            float _Specular;
            float _SpecularPower;
            float _GlossBoost;
            float _GlossSharpness;
            float _GlossHaloIntensity;
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

                float glossSharpMask = SoftMaskAlpha(
                    saturate(mask.a),
                    max(_Threshold * 0.96, 0.022),
                    max(lerp(0.044, 0.032, saturate(_GlossSharpness)), 0.032))
                    * fullSoft
                    * fullCore;
                float glossHaloMask = SoftMaskAlpha(
                    saturate(max(softMask.a, mask.a * 0.52)),
                    max(_Threshold * 0.70, 0.018),
                    max(_Feather * 0.26, 0.050))
                    * fullSoft
                    * fullCore;
                float glossHalo = saturate(glossHaloMask - glossSharpMask * 0.56);
                float glossEnergy = coverage
                    * coverage
                    * saturate(_Specular)
                    * saturate(_GlossBoost)
                    * saturate(_Opacity)
                    * saturate(_VisibilityAlpha);
                float sharpHighlight = glossSharpMask * glossEnergy * 0.96;
                float haloHighlight = glossHalo * glossEnergy * saturate(_GlossHaloIntensity) * 0.22;
                float3 glossScreenLift = saturate(1.0 - _RegionColor.rgb * 0.56);
                float3 sharpHighlightColor = saturate(lerp(_RegionColor.rgb, _GlossColor.rgb, 0.34));
                float3 haloHighlightColor = saturate(lerp(_RegionColor.rgb, _GlossColor.rgb, 0.03));
                float3 additiveGloss = sharpHighlightColor * glossScreenLift * sharpHighlight
                    + haloHighlightColor * glossScreenLift * haloHighlight;
                return fixed4(additiveGloss, 0.0);
            }
            ENDCG
        }
    }
}
