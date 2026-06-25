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

            fixed4 frag(v2f input) : SV_Target
            {
                float2 maskUv = input.uv;
                if (_UseScreenSpaceMask > 0.5)
                {
                    float2 ndc = input.clipPos.xy / max(input.clipPos.w, 0.00001);
                    maskUv = saturate(ndc * 0.5 + 0.5);
                }

                float4 mask = tex2D(_MaskTex, maskUv);
                float probability = mask.r;
                float high = min(1.0, _Threshold + max(_Feather, 0.00001));
                float fullAlpha = smoothstep(_Threshold, high, probability);
                float overlineAlpha = smoothstep(_Threshold, high, mask.g);
                float gradientAlpha = smoothstep(_Threshold, high, mask.b);
                float coverage = saturate(max(_Coverage, 0.001));
                float maskStrength = fullAlpha * coverage;
                float3 pigmentColor = saturate(_RegionColor.rgb);
                float3 alphaColor = pigmentColor;

                if (_LipStyleMode > -0.5)
                {
                    if (_LipStyleMode < 0.5)
                    {
                        maskStrength = fullAlpha * coverage;
                        pigmentColor = saturate(lerp(pigmentColor, pigmentColor * 0.88, saturate(_Roughness) * 0.2));
                        alphaColor = pigmentColor;
                    }
                    else if (_LipStyleMode < 1.5)
                    {
                        maskStrength = fullAlpha * coverage;
                        pigmentColor = saturate(lerp(pigmentColor, _SecondaryColor.rgb, 0.08));
                        alphaColor = saturate(lerp(pigmentColor, _SecondaryColor.rgb, 0.035) * 1.04);
                    }
                    else if (_LipStyleMode < 2.5)
                    {
                        maskStrength = saturate(max(fullAlpha, overlineAlpha * 0.18) * coverage);
                        pigmentColor = saturate(lerp(pigmentColor, pigmentColor * 0.88, 0.12));
                        alphaColor = pigmentColor;
                    }
                    else if (_LipStyleMode < 3.5)
                    {
                        float gradientMix = saturate(_GradientAmount);
                        float edgeStrength = fullAlpha * coverage * lerp(0.64, 0.42, gradientMix);
                        float innerDensity = saturate(gradientAlpha * (0.54 + gradientMix * 0.46));
                        maskStrength = saturate(edgeStrength + fullAlpha * coverage * innerDensity * gradientMix * 0.58);
                        pigmentColor = saturate(lerp(_SecondaryColor.rgb, pigmentColor, saturate(innerDensity + 0.12)));
                        alphaColor = pigmentColor;
                    }
                    else
                    {
                        float lineAlpha = saturate(overlineAlpha - fullAlpha * 0.45);
                        maskStrength = max(fullAlpha * coverage * 0.56, lineAlpha * coverage);
                        pigmentColor = saturate(lerp(_SecondaryColor.rgb, pigmentColor, fullAlpha));
                        alphaColor = pigmentColor;
                    }
                }

                float preserveScale = lerp(1.0, 0.92, saturate(_PreserveDetail));
                float opacity = saturate(_Opacity * _VisibilityAlpha);

                if (_PigmentMultiply > 0.5)
                {
                    float pigmentStrength = saturate(maskStrength * opacity * preserveScale);
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
                float high = min(1.0, _Threshold + max(_Feather, 0.00001));
                float fullAlpha = smoothstep(_Threshold, high, mask.r);
                float glossAlpha = smoothstep(_Threshold, high, mask.a);
                float coverage = saturate(max(_Coverage, 0.001));
                float glossMask = glossAlpha
                    * fullAlpha
                    * coverage
                    * saturate(_Specular)
                    * saturate(_GlossBoost)
                    * saturate(_Opacity)
                    * saturate(_VisibilityAlpha);

                float2 lipUv = input.uv - float2(0.5, 0.5);
                float centerWidth = 1.0 - smoothstep(0.06, 0.25, abs(lipUv.x));
                float lowerBand = 1.0 - smoothstep(0.012, 0.046, abs(lipUv.y + 0.026));
                float upperBand = 1.0 - smoothstep(0.012, 0.05, abs(lipUv.y - 0.036));
                float mouthGap = smoothstep(0.004, 0.026, abs(lipUv.y));
                float wetLine = glossMask * mouthGap * centerWidth * (
                    lowerBand * 0.72 + upperBand * 0.3);
                float fineStreaks = pow(saturate(sin(input.uv.x * 164.0 + 0.7) * 0.5 + 0.5), 18.0)
                    * glossMask
                    * mouthGap
                    * lowerBand
                    * centerWidth
                    * 0.28;
                float pinHighlight = pow(saturate(glossAlpha), max(_SpecularPower, 1.0) / 14.0)
                    * glossMask
                    * centerWidth
                    * 0.12;
                float highlight = saturate(wetLine + fineStreaks + pinHighlight);
                return fixed4(float3(1.0, 0.97, 0.92) * highlight, 0.0);
            }
            ENDCG
        }
    }
}
