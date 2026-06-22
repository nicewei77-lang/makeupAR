Shader "MakeupAR/E7ReferenceUvAlphaMask"
{
    Properties
    {
        _MaskTex ("Mask Texture", 2D) = "black" {}
        _RegionColor ("Region Color", Color) = (0.85, 0.29, 0.45, 1)
        _Opacity ("Opacity", Range(0, 1)) = 0.65
        _Threshold ("Threshold", Range(0, 1)) = 0.45
        _Feather ("Feather", Range(0, 0.1)) = 0.00390625
        _VisibilityAlpha ("Visibility Alpha", Range(0, 1)) = 1
        _VisibilityBoost ("Validation Visibility Boost", Range(1, 2)) = 1.35
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
            float _VisibilityBoost;

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
                float feather = max(_Feather, 0.00001);
                float alpha = smoothstep(_Threshold - feather, _Threshold + feather, probability)
                    * _Opacity
                    * _VisibilityAlpha
                    * _VisibilityBoost;
                return fixed4(_RegionColor.rgb, saturate(alpha));
            }
            ENDCG
        }
    }
}
