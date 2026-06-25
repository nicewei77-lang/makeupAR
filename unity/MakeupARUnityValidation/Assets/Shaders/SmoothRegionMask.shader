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
            Name "BuiltInUnlitAlpha"
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

            struct appdata
            {
                float4 vertex : POSITION;
                float2 uv : TEXCOORD0;
            };

            struct v2f
            {
                float4 vertex : SV_POSITION;
                float2 uv : TEXCOORD0;
            };

            v2f vert(appdata input)
            {
                v2f output;
                output.vertex = UnityObjectToClipPos(input.vertex);
                output.uv = input.uv;
                return output;
            }

            fixed4 frag(v2f input) : SV_Target
            {
                float4 mask = tex2D(_MaskTex, input.uv);
                float probability = mask.r;
                float high = min(1.0, _Threshold + max(_Feather, 0.00001));
                float fullAlpha = smoothstep(_Threshold, high, probability);
                float overlineAlpha = smoothstep(_Threshold, high, mask.g);
                float gradientAlpha = smoothstep(_Threshold, high, mask.b);
                float glossAlpha = _LipStyleMode > -0.5
                    ? smoothstep(_Threshold, high, mask.a)
                    : fullAlpha;

                float coverage = saturate(max(_Coverage, 0.001));
                float alpha = fullAlpha * coverage;
                float3 color = _RegionColor.rgb;

                if (_LipStyleMode > -0.5)
                {
                    if (_LipStyleMode < 0.5)
                    {
                        alpha = fullAlpha * coverage;
                        color = lerp(color, color * 0.92, saturate(_Roughness));
                    }
                    else if (_LipStyleMode < 1.5)
                    {
                        alpha = fullAlpha * coverage;
                        color = lerp(color, _SecondaryColor.rgb, 0.08);
                        float glossMask = glossAlpha * fullAlpha * saturate(_GlossBoost);
                        float softSheen = pow(saturate(glossMask), 0.82) * 0.46;
                        color = saturate(color + float3(1.0, 0.96, 0.92) * softSheen);
                        alpha = saturate(alpha + glossMask * 0.14);
                    }
                    else if (_LipStyleMode < 2.5)
                    {
                        alpha = saturate(max(fullAlpha, overlineAlpha * 0.18) * coverage);
                        color = lerp(color, color * 0.86, 0.18);
                    }
                    else if (_LipStyleMode < 3.5)
                    {
                        float gradientMix = saturate(_GradientAmount);
                        alpha = lerp(fullAlpha * 0.36, gradientAlpha, gradientMix) * coverage;
                        color = lerp(_SecondaryColor.rgb, color, saturate(gradientAlpha + 0.18));
                    }
                    else
                    {
                        float lineAlpha = saturate(overlineAlpha - fullAlpha * 0.45);
                        alpha = max(fullAlpha * coverage * 0.56, lineAlpha * coverage);
                        color = lerp(_SecondaryColor.rgb, color, fullAlpha);
                    }
                }

                float preserveScale = lerp(1.0, 0.86, saturate(_PreserveDetail));
                float highlight = (_LipStyleMode > 0.5 && _LipStyleMode < 1.5 ? glossAlpha * fullAlpha : 0.0)
                    * saturate(_Specular)
                    * saturate(_GlossBoost)
                    * pow(saturate(glossAlpha), max(_SpecularPower, 1.0) / 32.0);
                color = saturate(color + highlight * 0.36);
                alpha = alpha * _Opacity * _VisibilityAlpha * preserveScale;
                return fixed4(color, saturate(alpha));
            }
            ENDCG
        }
    }
}
