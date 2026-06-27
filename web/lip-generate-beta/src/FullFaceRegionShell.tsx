import compositePackageJson from '../../../evidence/e7-region-generate/session-20260626T195853Z/composite_apply_payload.json';
import blushScorecardJson from '../../../evidence/e7-region-generate/session-20260626T195853Z/regions/blush/scorecard.json';
import browScorecardJson from '../../../evidence/e7-region-generate/session-20260626T195853Z/regions/brow/scorecard.json';
import eyelinerScorecardJson from '../../../evidence/e7-region-generate/session-20260626T195853Z/regions/eyeliner/scorecard.json';
import lipScorecardJson from '../../../evidence/e7-region-generate/session-20260626T195853Z/regions/lip/scorecard.json';
import { useMemo, useState } from 'react';

type RegionKey = 'lip' | 'blush' | 'brow' | 'eyeliner';

type RegionAdjustment = Record<string, number>;

type RegionPackage = {
  region: RegionKey;
  status: string;
  selectedPolicy: string;
  adjustment: RegionAdjustment;
  qualityWarnings: string[];
  runtimeApplyPayload: Record<string, unknown>;
  uvMask: {
    roundTripStatus: string;
    roundTripScore: {
      iou: number;
      precision: number;
      recall: number;
      candidatePositivePixels: number;
      referencePositivePixels: number;
    };
  };
};

type FullFaceCompositePackage = {
  schemaVersion: string;
  sessionId: string;
  status: string;
  regionDecisions: Record<RegionKey, string>;
  packages: Record<RegionKey, RegionPackage>;
  runtimeApplyPayload: {
    schemaVersion: string;
    packageId: string;
    preXcodeReady: boolean;
    runtimeReady: boolean;
    localOnly: boolean;
    offDeviceUpload: boolean;
    longTermRawFrameStored: boolean;
    regions: Record<RegionKey, Record<string, unknown>>;
  };
};

type RegionScorecard = {
  region: RegionKey;
  decision: string;
  selectedCandidateId: string;
  selectedPolicy: string;
  candidateCount: number;
  candidateReports: Array<{
    candidateId: string;
    policy: string;
    warnings: string[];
    shape: {
      positivePixels: number;
      bbox: Record<string, number>;
    };
    uvProjection: {
      sampleStride: number;
      recommendedThreshold: number;
      roundTrip: RegionPackage['uvMask']['roundTripScore'];
    };
  }>;
};

type RegionAdjustmentState = Record<RegionKey, RegionAdjustment>;

const fullFaceComposite = compositePackageJson as FullFaceCompositePackage;

const REGION_KEYS: RegionKey[] = ['lip', 'blush', 'brow', 'eyeliner'];

const REGION_LABELS: Record<RegionKey, string> = {
  lip: 'Lip',
  blush: 'Blush',
  brow: 'Brow',
  eyeliner: 'Eyeliner',
};

const REGION_SCORECARDS: Record<RegionKey, RegionScorecard> = {
  lip: lipScorecardJson as RegionScorecard,
  blush: blushScorecardJson as RegionScorecard,
  brow: browScorecardJson as RegionScorecard,
  eyeliner: eyelinerScorecardJson as RegionScorecard,
};

const ROOT_CONTACT_SHEET_URL = new URL(
  '../../../evidence/e7-region-generate/session-20260626T195853Z/contact_sheet.png',
  import.meta.url,
).href;

const REGION_CONTACT_SHEET_URLS: Record<RegionKey, string> = {
  lip: new URL(
    '../../../evidence/e7-region-generate/session-20260626T195853Z/regions/lip/contact_sheet.png',
    import.meta.url,
  ).href,
  blush: new URL(
    '../../../evidence/e7-region-generate/session-20260626T195853Z/regions/blush/contact_sheet.png',
    import.meta.url,
  ).href,
  brow: new URL(
    '../../../evidence/e7-region-generate/session-20260626T195853Z/regions/brow/contact_sheet.png',
    import.meta.url,
  ).href,
  eyeliner: new URL(
    '../../../evidence/e7-region-generate/session-20260626T195853Z/regions/eyeliner/contact_sheet.png',
    import.meta.url,
  ).href,
};

function initialRegionAdjustments(): RegionAdjustmentState {
  return REGION_KEYS.reduce((acc, region) => {
    acc[region] = { ...fullFaceComposite.packages[region].adjustment };
    return acc;
  }, {} as RegionAdjustmentState);
}

export function FullFaceRegionShell({
  onOpenAppShell,
  onOpenLipBeta,
}: {
  onOpenAppShell: () => void;
  onOpenLipBeta: () => void;
}) {
  const [selectedRegion, setSelectedRegion] = useState<RegionKey>('lip');
  const [adjustments, setAdjustments] = useState<RegionAdjustmentState>(
    initialRegionAdjustments,
  );
  const [saveMessage, setSaveMessage] = useState('저장 대기');

  const selectedPackage = fullFaceComposite.packages[selectedRegion];
  const selectedScorecard = REGION_SCORECARDS[selectedRegion];
  const selectedReport =
    selectedScorecard.candidateReports.find(
      report => report.candidateId === selectedScorecard.selectedCandidateId,
    ) ?? selectedScorecard.candidateReports[0];
  const adjustedPayload = useMemo(
    () => buildAdjustedCompositePayload(adjustments),
    [adjustments],
  );

  function updateAxis(axis: string, nextValue: number) {
    setAdjustments(previous => ({
      ...previous,
      [selectedRegion]: {
        ...previous[selectedRegion],
        [axis]: Number(nextValue.toFixed(3)),
      },
    }));
    setSaveMessage('저장 대기');
  }

  function resetRegion() {
    setAdjustments(previous => ({
      ...previous,
      [selectedRegion]: {
        ...fullFaceComposite.packages[selectedRegion].adjustment,
      },
    }));
    setSaveMessage('저장 대기');
  }

  function savePayloadDraft() {
    window.localStorage.setItem(
      'e7-full-face-region-package-draft',
      JSON.stringify(adjustedPayload),
    );
    setSaveMessage('localStorage 저장 완료');
  }

  return (
    <main className="app-shell full-face-shell">
      <header className="toolbar">
        <div>
          <h1>E7 Full-Face Generate</h1>
          <p className="status-line" data-tone="warn">
            {fullFaceComposite.status} · pre-Xcode · iPhone evidence pending
          </p>
        </div>
        <div className="toolbar-actions">
          <button type="button" onClick={onOpenAppShell}>
            App shell
          </button>
          <button type="button" onClick={onOpenLipBeta}>
            Lip beta
          </button>
          <button type="button" onClick={resetRegion}>
            선택 초기화
          </button>
          <button type="button" className="primary" onClick={savePayloadDraft}>
            패키지 저장
          </button>
        </div>
      </header>

      <section className="workspace full-face-workspace">
        <aside className="control-panel">
          <section className="panel-section">
            <div className="step-heading">
              <span>Step 1</span>
              <h2>Region 선택</h2>
            </div>
            <div className="region-tabs" role="tablist" aria-label="Region">
              {REGION_KEYS.map(region => (
                <button
                  key={region}
                  type="button"
                  className="region-tab"
                  data-active={selectedRegion === region}
                  onClick={() => setSelectedRegion(region)}
                >
                  <strong>{REGION_LABELS[region]}</strong>
                  <span>{fullFaceComposite.regionDecisions[region]}</span>
                </button>
              ))}
            </div>
          </section>

          <section className="panel-section">
            <div className="section-heading compact">
              <div className="step-heading">
                <span>Step 2</span>
                <h2>조정 축</h2>
              </div>
              <button type="button" onClick={resetRegion}>
                Reset
              </button>
            </div>
            <RegionAdjustmentPanel
              region={selectedRegion}
              adjustment={adjustments[selectedRegion]}
              onChange={updateAxis}
            />
          </section>

          <section className="panel-section">
            <div className="step-heading">
              <span>Step 4</span>
              <h2>Gate</h2>
            </div>
            <RegionGateList
              packageData={selectedPackage}
              scorecard={selectedScorecard}
            />
          </section>
        </aside>

        <section className="inspect-panel">
          <section className="result-summary" data-status="partial">
            <div>
              <span className="eyebrow">Saved package</span>
              <h2>{REGION_LABELS[selectedRegion]} · {selectedPackage.selectedPolicy}</h2>
            </div>
            <div className="summary-chips">
              <span>{selectedScorecard.candidateCount} candidates</span>
              <span>IoU {selectedReport.uvProjection.roundTrip.iou}</span>
              <span>threshold {selectedReport.uvProjection.recommendedThreshold}</span>
              <span>{saveMessage}</span>
            </div>
          </section>

          <section className="full-face-grid">
            <ImageCard title="Composite contact sheet" src={ROOT_CONTACT_SHEET_URL} />
            <ImageCard
              title={`${REGION_LABELS[selectedRegion]} contact sheet`}
              src={REGION_CONTACT_SHEET_URLS[selectedRegion]}
            />
          </section>

          <section className="region-card-grid">
            {REGION_KEYS.map(region => (
              <RegionCard
                key={region}
                region={region}
                isSelected={region === selectedRegion}
                scorecard={REGION_SCORECARDS[region]}
                packageData={fullFaceComposite.packages[region]}
                onSelect={() => setSelectedRegion(region)}
              />
            ))}
          </section>

          <details className="payload-section debug-section" open>
            <summary>
              <strong>Runtime payload</strong>
              <span>RN/Unity handoff draft</span>
            </summary>
            <pre>{JSON.stringify(compactPayloadForDisplay(adjustedPayload), null, 2)}</pre>
          </details>
        </section>
      </section>
    </main>
  );
}

function RegionAdjustmentPanel({
  region,
  adjustment,
  onChange,
}: {
  region: RegionKey;
  adjustment: RegionAdjustment;
  onChange: (axis: string, value: number) => void;
}) {
  return (
    <div className="range-stack">
      {(Object.entries(adjustment) as Array<[string, number]>).map(
        ([axis, value]) => {
          const range = rangeForAxis(region, axis, value);
          return (
            <div className="range-row region-axis-row" key={axis}>
              <label htmlFor={`region-${region}-${axis}`}>
                <span>{axis}</span>
                <div className="range-control">
                  <button
                    type="button"
                    aria-label={`${axis} 줄이기`}
                    onClick={() => onChange(axis, Math.max(range.min, value - range.step))}
                  >
                    -
                  </button>
                  <input
                    id={`region-${region}-${axis}`}
                    aria-label={axis}
                    type="range"
                    min={range.min}
                    max={range.max}
                    step={range.step}
                    value={value}
                    onChange={event => onChange(axis, Number(event.currentTarget.value))}
                  />
                  <button
                    type="button"
                    aria-label={`${axis} 늘리기`}
                    onClick={() => onChange(axis, Math.min(range.max, value + range.step))}
                  >
                    +
                  </button>
                </div>
              </label>
              <output htmlFor={`region-${region}-${axis}`}>
                {value.toFixed(range.step < 1 ? 2 : 0)}
              </output>
            </div>
          );
        },
      )}
    </div>
  );
}

function RegionGateList({
  packageData,
  scorecard,
}: {
  packageData: RegionPackage;
  scorecard: RegionScorecard;
}) {
  const rows = [
    ['후보 생성', `${scorecard.candidateCount}개`],
    ['선택 정책', packageData.selectedPolicy],
    ['UV round-trip', packageData.uvMask.roundTripStatus],
    ['iPhone 적용', packageData.status === 'preXcodeReady' ? '검증 전' : packageData.status],
  ];

  return (
    <div className="gate-steps">
      <div className="gate-status">
        <span>현재 판정</span>
        <strong>{scorecard.decision}</strong>
      </div>
      {rows.map(([label, value]) => (
        <div className="gate-step" data-state="done" key={label}>
          <span>{label}</span>
          <strong>{value}</strong>
        </div>
      ))}
    </div>
  );
}

function RegionCard({
  region,
  isSelected,
  scorecard,
  packageData,
  onSelect,
}: {
  region: RegionKey;
  isSelected: boolean;
  scorecard: RegionScorecard;
  packageData: RegionPackage;
  onSelect: () => void;
}) {
  const selectedReport =
    scorecard.candidateReports.find(
      report => report.candidateId === scorecard.selectedCandidateId,
    ) ?? scorecard.candidateReports[0];
  return (
    <button
      type="button"
      className="region-card"
      data-active={isSelected}
      onClick={onSelect}
    >
      <strong>{REGION_LABELS[region]}</strong>
      <span>{packageData.selectedPolicy}</span>
      <small>
        IoU {selectedReport.uvProjection.roundTrip.iou} · recall{' '}
        {selectedReport.uvProjection.roundTrip.recall}
      </small>
    </button>
  );
}

function ImageCard({ title, src }: { title: string; src: string }) {
  return (
    <figure className="full-face-image-card">
      <figcaption>{title}</figcaption>
      <img src={src} alt={title} />
    </figure>
  );
}

function buildAdjustedCompositePayload(
  adjustments: RegionAdjustmentState,
): FullFaceCompositePackage & {
  webValidation: {
    savedFrom: string;
    iPhoneEvidenceRequiredForGreen: true;
  };
} {
  const packages = REGION_KEYS.reduce((acc, region) => {
    acc[region] = {
      ...fullFaceComposite.packages[region],
      adjustment: adjustments[region],
    };
    return acc;
  }, {} as Record<RegionKey, RegionPackage>);

  const runtimeRegions = REGION_KEYS.reduce((acc, region) => {
    acc[region] = {
      ...fullFaceComposite.runtimeApplyPayload.regions[region],
      adjustment: adjustments[region],
    };
    return acc;
  }, {} as Record<RegionKey, Record<string, unknown>>);

  return {
    ...fullFaceComposite,
    packages,
    runtimeApplyPayload: {
      ...fullFaceComposite.runtimeApplyPayload,
      regions: runtimeRegions,
    },
    webValidation: {
      savedFrom: 'web/lip-generate-beta full-face shell',
      iPhoneEvidenceRequiredForGreen: true,
    },
  };
}

function rangeForAxis(region: RegionKey, axis: string, value: number) {
  const lower = axis.toLowerCase();
  if (lower.includes('angle')) {
    return { min: -45, max: 45, step: 1 };
  }
  if (lower.includes('offset')) {
    return { min: -80, max: 80, step: 1 };
  }
  if (lower.includes('thickness')) {
    return { min: 0, max: region === 'eyeliner' ? 20 : 36, step: 1 };
  }
  if (lower.includes('height')) {
    return { min: 0, max: 70, step: 1 };
  }
  if (
    lower.includes('intensity') ||
    lower.includes('feather') ||
    lower.includes('softness') ||
    lower.includes('guard') ||
    lower.includes('fade')
  ) {
    return { min: 0, max: 1, step: 0.05 };
  }
  if (lower.includes('tail') || lower.includes('coverage') || lower.includes('size')) {
    return { min: 0, max: Math.max(1.5, value * 1.5), step: 0.05 };
  }
  return { min: -1, max: 1, step: 0.05 };
}

function compactPayloadForDisplay(value: unknown): unknown {
  if (Array.isArray(value)) {
    return value.map(item => compactPayloadForDisplay(item));
  }

  if (value && typeof value === 'object') {
    return Object.fromEntries(
      Object.entries(value).map(([key, entry]) => {
        if (
          (key.toLowerCase().includes('base64') || key.toLowerCase().includes('raw')) &&
          typeof entry === 'string'
        ) {
          return [key, `[omitted ${entry.length} chars]`];
        }
        return [key, compactPayloadForDisplay(entry)];
      }),
    );
  }

  return value;
}
