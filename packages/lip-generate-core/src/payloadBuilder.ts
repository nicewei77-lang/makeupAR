import {
  LipAdjustment,
  LipGeneratePackage,
  LipMaskProvider,
  LipRuntimeApplyPayload,
} from './contracts';

type BuildRuntimePayloadInput = {
  generatedMaskId: string;
  provider: LipMaskProvider;
  expressionMode: LipRuntimeApplyPayload['expressionMode'];
  adjustment: LipAdjustment;
  maskTexturePath?: string;
  maskTextureId?: string;
  maskThreshold?: number;
  maskFeatherUvNormalized?: number;
  runtimeReady?: boolean;
};

export function buildRuntimeApplyPayload({
  generatedMaskId,
  provider,
  expressionMode,
  adjustment,
  maskTexturePath,
  maskTextureId,
  maskThreshold = 0.5,
  maskFeatherUvNormalized = 0.07,
  runtimeReady = false,
}: BuildRuntimePayloadInput): LipRuntimeApplyPayload {
  return {
    schemaVersion: 'e7-generated-lip-mask-runtime-payload-v0',
    generatedMaskId,
    provider,
    expressionMode,
    adjustment,
    maskTexturePath,
    maskTextureId,
    maskThreshold,
    maskFeatherUvNormalized,
    localOnly: true,
    runtimeReady,
  };
}

export function buildUnityMessageFromPackage(
  generatedPackage: LipGeneratePackage,
) {
  return {
    type: 'apply_generated_lip_mask',
    schemaVersion: generatedPackage.runtimeApplyPayload.schemaVersion,
    generatedMaskId: generatedPackage.generatedMaskId,
    provider: generatedPackage.provider,
    expressionMode: generatedPackage.expressionMode,
    adjustment: generatedPackage.adjustment,
    maskTexturePath: generatedPackage.runtimeApplyPayload.maskTexturePath,
    maskTextureId: generatedPackage.runtimeApplyPayload.maskTextureId,
    maskThreshold: generatedPackage.runtimeApplyPayload.maskThreshold,
    maskFeatherUvNormalized:
      generatedPackage.runtimeApplyPayload.maskFeatherUvNormalized,
    localOnly: true,
    runtimeReady: generatedPackage.runtimeApplyPayload.runtimeReady,
  };
}
