import {
  DEFAULT_LIP_ADJUSTMENT,
  ExpressionAssistMode,
  LipAdjustment,
  LipGeneratePackage,
  LipGenerateRequest,
  LipGenerateResult,
  LipMaskProvider,
} from '../../../packages/lip-generate-core/src';
import {
  LipGenerateFixture,
  LipGenerateFixtureInventory,
} from '../../../packages/lip-generate-core/src/fixtureInventory';

export const LOCAL_SERVER_URL = 'http://127.0.0.1:8791';

export type ServerGenerateResult = LipGenerateResult & {
  runId?: string;
  runDirectory?: string;
  maskOutputs?: {
    mask?: string;
    alpha?: string;
    overlay?: string;
    boundary?: string;
  };
  package?: LipGeneratePackage;
};

export type SavedLipPackageRecord = {
  schemaVersion: 'e7-lip-generate-saved-record-v0';
  savedAt: string;
  generatedMaskId: string;
  provider: LipMaskProvider;
  expressionMode: ExpressionAssistMode;
  adjustment: LipAdjustment;
  status: 'saved_local_only';
  packagePath: string;
  metadataPath: string;
  roundTripPreview?: string;
  uvMaskTexture?: string;
  privacyFlags: {
    localOnly: true;
    offDeviceUpload: false;
    longTermRawFrameStored: false;
  };
  runtimeReady: boolean;
};

export type SavedLipPackageList = {
  schemaVersion: 'e7-lip-generate-saved-list-v0';
  status: string;
  records: SavedLipPackageRecord[];
};

export async function fetchFixtures(): Promise<LipGenerateFixtureInventory> {
  const response = await fetch(`${LOCAL_SERVER_URL}/api/lip-mask/fixtures`);
  if (!response.ok) {
    throw new Error(`fixture fetch failed: ${response.status}`);
  }
  return response.json() as Promise<LipGenerateFixtureInventory>;
}

export function buildGenerateRequest(input: {
  provider: LipMaskProvider;
  expressionMode: ExpressionAssistMode;
  adjustment: LipAdjustment;
  fixtureId: string;
}): LipGenerateRequest {
  return {
    requestId: `web-react-${Date.now()}`,
    provider: input.provider,
    expressionMode: input.expressionMode,
    adjustment: input.adjustment,
    frameSource: 'fixture',
    fixtureId: input.fixtureId,
    privacy: {
      localOnly: true,
      offDeviceUpload: false,
      longTermRawFrameStored: false,
    },
  };
}

export async function generateLipMask(
  request: LipGenerateRequest,
): Promise<ServerGenerateResult> {
  const response = await fetch(`${LOCAL_SERVER_URL}/api/lip-mask/generate`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });
  const data = (await response.json()) as ServerGenerateResult & {
    reason?: string;
    blockers?: string[];
  };
  if (!response.ok) {
    throw new Error(data.reason || data.blockers?.join(', ') || 'generate failed');
  }
  return data;
}

export async function fetchSavedPackages(): Promise<SavedLipPackageRecord[]> {
  const response = await fetch(`${LOCAL_SERVER_URL}/api/lip-mask/saved`);
  const data = (await response.json()) as SavedLipPackageList & {
    reason?: string;
  };
  if (!response.ok) {
    throw new Error(data.reason || 'saved package fetch failed');
  }
  return data.records ?? [];
}

export async function saveGeneratedPackage(
  result: ServerGenerateResult,
): Promise<SavedLipPackageRecord> {
  if (!result.package || !result.runDirectory) {
    throw new Error('저장할 generated package가 없습니다.');
  }
  const response = await fetch(`${LOCAL_SERVER_URL}/api/lip-mask/save`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      generatedMaskId: result.generatedMaskId,
      packagePath: `${result.runDirectory}/generated_lip_package.json`,
    }),
  });
  const data = (await response.json()) as {
    status: string;
    record?: SavedLipPackageRecord;
    blockers?: string[];
    reason?: string;
  };
  if (!response.ok || !data.record) {
    throw new Error(data.reason || data.blockers?.join(', ') || 'save failed');
  }
  return data.record;
}

export function artifactUrl(path?: string): string {
  if (!path) {
    return '';
  }
  const encoded = encodeURIComponent(path);
  return `${LOCAL_SERVER_URL}/api/lip-mask/artifact?path=${encoded}`;
}

export function defaultAdjustment(): LipAdjustment {
  return { ...DEFAULT_LIP_ADJUSTMENT };
}

export function fixtureLabel(fixture: LipGenerateFixture): string {
  return fixture.label || fixture.fixtureId;
}
