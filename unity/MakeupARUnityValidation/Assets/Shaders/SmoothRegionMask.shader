Shader "MakeupAR/SmoothRegionMask"
{
    Properties
    {
        _MaskTex ("Mask Texture", 2D) = "black" {}
        _RegionColor ("Region Color", Color) = (0.85, 0.29, 0.45, 1)
        _Opacity ("Opacity", Range(0, 1)) = 0.65
        _Threshold ("Threshold", Range(0, 1)) = 0.04
        _Feather ("Feather", Range(0, 1)) = 0.5
        _VisibilityAlpha ("Visibility Alpha", Range(0, 1)) = 1
        _Coverage ("Coverage", Range(0, 1)) = 0.7
        _TextureAmount ("Texture Amount", Range(0, 1)) = 0
        _FinishMode ("Finish Mode", Range(-1, 2)) = -1
        _Roughness ("Roughness", Range(0, 1)) = 0.6
        _Specular ("Specular", Range(0, 1)) = 0
        _SpecularPower ("Specular Power", Range(0, 128)) = 16
        _GlossBoost ("Gloss Boost", Range(0, 1)) = 0
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

            Blend SrcAlpha OneMinusSrcAlpha
            ZWrite Off
            ZTest Always
            Cull Off

            CGPROGRAM
            #pragma vertex vert
            #pragma fragment frag

            #include "UnityCG.cginc"

            sampler2D _MaskTex;
            float4 _RegionColor;
            float _Opacity;
            float _Threshold;
            float _Feather;
            float _VisibilityAlpha;
            float _Coverage;
            float _TextureAmount;
            float _FinishMode;
            float _Roughness;
            float _Specular;
            float _SpecularPower;
            float _GlossBoost;

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
                float probability = tex2D(_MaskTex, input.uv).r;
                float coverage = saturate(_Coverage);
                float threshold = saturate(_Threshold + (0.70 - coverage) * 0.08);
                float high = min(1.0, threshold + max(_Feather, 0.00001));
                float alpha = smoothstep(threshold, high, probability)
                    * _Opacity
                    * _VisibilityAlpha;
                float grain = frac(sin(dot(input.uv * 173.0, float2(12.9898, 78.233))) * 43758.5453);
                float grainScale = 1.0 + (grain - 0.5) * saturate(_TextureAmount) * 0.16;
                float3 color = saturate(_RegionColor.rgb * grainScale);

                float horizontalCenter = saturate(1.0 - abs(input.uv.x - 0.5) * 2.0);
                float lowerLipBand = smoothstep(0.36, 0.52, input.uv.y)
                    * (1.0 - smoothstep(0.68, 0.82, input.uv.y));
                float highlightShape = pow(horizontalCenter, 3.0) * lowerLipBand * saturate(alpha);
                float specularShape = pow(saturate(highlightShape), max(1.0, _SpecularPower / 12.0));
                float specularStrength = saturate(_Specular + _GlossBoost) * saturate(1.0 - _Roughness);

                if (_FinishMode > 1.5)
                {
                    color += float3(1.0, 0.94, 0.9) * specularShape * specularStrength;
                }
                else if (_FinishMode > 0.5)
                {
                    color += float3(1.0, 0.86, 0.78) * highlightShape * _Specular * 0.22;
                }

                return fixed4(saturate(color), saturate(alpha));
            }
            ENDCG
        }
    }
}
