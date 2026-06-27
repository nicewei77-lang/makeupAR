import { useMemo, useState } from 'react';

type WizardStepId =
  | 'start'
  | 'align'
  | 'capture'
  | 'extract'
  | 'compare'
  | 'adjust'
  | 'save'
  | 'runtime';

type CaptureShotState = 'ready' | 'active' | 'blocked';

type WizardStep = {
  id: WizardStepId;
  index: number;
  title: string;
  subtitle: string;
  gate: string;
  state: 'ready' | 'active' | 'locked';
};

type CandidatePreview = {
  id: string;
  title: string;
  status: string;
  src: string;
};

type ExtractionProvider = 'vision' | 'mediapipe';

const FACE_FRAME_URL = new URL(
  '../../../evidence/e7-reference-atlas/capture_pairs/pair_face_20260622T143334Z_03/frame.png',
  import.meta.url,
).href;

const MESH_OVERLAY_URL = new URL(
  '../../../evidence/e7-reference-atlas/capture_pairs/pair_face_20260622T143334Z_03/projected_mesh_overlay.png',
  import.meta.url,
).href;

const VISION_OVERLAY_URL = new URL(
  '../../../evidence/e7-lip-generate-server/inspect-vision-baseline-vision-uvOnly/vision_lip_overlay.png',
  import.meta.url,
).href;

const MEDIAPIPE_OVERLAY_URL = new URL(
  '../../../evidence/e7-lip-generate-server/inspect-mediapipe-baseline-mediapipe-uvOnly/mediapipe_lip_overlay.png',
  import.meta.url,
).href;

const ROUND_TRIP_URL = new URL(
  '../../../evidence/e7-lip-generate-server/inspect-vision-baseline-vision-uvOnly/vision_projection/round_trip_overlay.png',
  import.meta.url,
).href;

const steps: WizardStep[] = [
  {
    id: 'start',
    index: 0,
    title: '시작',
    subtitle: '권한과 로컬 처리 확인',
    gate: 'AR 지원 / 카메라 권한 / 로컬 전용',
    state: 'ready',
  },
  {
    id: 'align',
    index: 1,
    title: '얼굴 정렬',
    subtitle: '거리, 밝기, 흔들림 확인',
    gate: 'face tracked / centered / blur ok',
    state: 'ready',
  },
  {
    id: 'capture',
    index: 2,
    title: '촬영',
    subtitle: '표정별 capture set 생성',
    gate: 'required shots ready',
    state: 'active',
  },
  {
    id: 'extract',
    index: 3,
    title: '추출',
    subtitle: 'native Vision / MediaPipe',
    gate: 'provider results ready',
    state: 'locked',
  },
  {
    id: 'compare',
    index: 4,
    title: '비교',
    subtitle: '4가지 후보 확인',
    gate: 'Vision/MediaPipe x assist off/on',
    state: 'locked',
  },
  {
    id: 'adjust',
    index: 5,
    title: '조정',
    subtitle: '입꼬리, 윗입술, 아랫입술, 위치',
    gate: 'mask / UV / payload delta',
    state: 'locked',
  },
  {
    id: 'save',
    index: 6,
    title: '저장',
    subtitle: 'stale 결과 차단',
    gate: 'package metadata complete',
    state: 'locked',
  },
  {
    id: 'runtime',
    index: 7,
    title: 'AR 준비',
    subtitle: 'Unity 적용 smoke',
    gate: 'Xcode build pending',
    state: 'locked',
  },
];

const captureShots: Array<{
  label: string;
  detail: string;
  state: CaptureShotState;
}> = [
  { label: 'Neutral', detail: '기준 얼굴', state: 'ready' },
  { label: 'Mouth open', detail: 'inner-mouth guard', state: 'ready' },
  { label: 'Mouth closed', detail: 'closed-lip baseline', state: 'ready' },
  { label: 'Smile', detail: 'corner stretch', state: 'active' },
  { label: 'Pucker', detail: 'projection stress', state: 'blocked' },
  { label: 'Yaw L/R', detail: 'visibility guard', state: 'blocked' },
];

const providerLabels: Record<ExtractionProvider, string> = {
  vision: 'Vision',
  mediapipe: 'MediaPipe',
};

function getProviderPreview(provider: ExtractionProvider) {
  return provider === 'vision' ? VISION_OVERLAY_URL : MEDIAPIPE_OVERLAY_URL;
}

function buildCandidates(provider: ExtractionProvider): CandidatePreview[] {
  const providerLabel = providerLabels[provider];
  const src = getProviderPreview(provider);

  return [
    {
      id: `${provider}-off`,
      title: `${providerLabel} / 기본`,
      status: 'blendshape assist off',
      src,
    },
    {
      id: `${provider}-blend`,
      title: `${providerLabel} / 보정`,
      status: 'blendshape assist on',
      src,
    },
    {
      id: `${provider}-soft`,
      title: `${providerLabel} / 부드럽게`,
      status: 'edge feather preview',
      src,
    },
    {
      id: `${provider}-safe`,
      title: `${providerLabel} / 안전`,
      status: 'spill-check preview',
      src,
    },
  ];
}

export function AppWizardShell({
  onOpenFullFace,
  onOpenLipBeta,
}: {
  onOpenFullFace: () => void;
  onOpenLipBeta: () => void;
}) {
  const [selectedStepId, setSelectedStepId] = useState<WizardStepId>('start');
  const [maxUnlockedIndex, setMaxUnlockedIndex] = useState(0);
  const [selectedProvider, setSelectedProvider] =
    useState<ExtractionProvider>('vision');
  const stepViews = useMemo(
    () =>
      steps.map(step => {
        const state: WizardStep['state'] =
          step.id === selectedStepId
            ? 'active'
            : step.index <= maxUnlockedIndex
              ? 'ready'
              : 'locked';

        return {
          ...step,
          state,
        };
      }),
    [maxUnlockedIndex, selectedStepId],
  );
  const selectedStep = useMemo(
    () => stepViews.find(step => step.id === selectedStepId) ?? stepViews[0],
    [selectedStepId, stepViews],
  );
  const selectedStepIndex = selectedStep.index;
  const candidates = useMemo(
    () => buildCandidates(selectedProvider),
    [selectedProvider],
  );
  const goToStep = (stepId: WizardStepId) => {
    const requestedStep = steps.find(step => step.id === stepId);
    if (!requestedStep || requestedStep.index > maxUnlockedIndex) {
      return;
    }

    setSelectedStepId(stepId);
  };
  const goNext = () => {
    const nextStep = steps[selectedStepIndex + 1];
    if (!nextStep) {
      return;
    }

    setMaxUnlockedIndex(current => Math.max(current, nextStep.index));
    setSelectedStepId(nextStep.id);
  };
  const goBack = () => {
    const previousStep = steps[selectedStepIndex - 1];
    if (previousStep) {
      setSelectedStepId(previousStep.id);
    }
  };

  return (
    <main className="app-shell wizard-shell">
      <header className="wizard-toolbar">
        <div>
          <span className="eyebrow">Web app shell</span>
          <h1>E7 Personalized Generate</h1>
          <p className="status-line" data-tone="warn">
            기능 없는 앱 UI 계약 · RN 이식 전 시각 승인용
          </p>
        </div>
        <div className="toolbar-actions">
          <button type="button" onClick={onOpenFullFace}>
            Full-face beta
          </button>
          <button type="button" onClick={onOpenLipBeta}>
            Functional beta
          </button>
        </div>
      </header>

      <section className="wizard-stage">
        <aside className="wizard-rail" aria-label="Wizard preview steps">
          {stepViews.map(step => (
            <button
              key={step.id}
              type="button"
              className="wizard-step-button"
              data-selected={step.id === selectedStep.id}
              data-state={step.state}
              disabled={step.state === 'locked'}
              onClick={() => goToStep(step.id)}
            >
              <span>{String(step.index + 1).padStart(2, '0')}</span>
              <strong>{step.title}</strong>
              <small>{step.gate}</small>
            </button>
          ))}
        </aside>

        <section className="phone-preview" aria-label="iPhone app shell preview">
          <div className="phone-device" data-step={selectedStep.id}>
            <div className="phone-dynamic-island">
              <span />
            </div>
            <div
              className="camera-scene"
              data-mode={selectedStep.index >= 3 ? 'captured' : 'live'}
            >
              <img src={FACE_FRAME_URL} alt="capture reference frame" />
              {selectedStep.index >= 3 && (
                <div className="camera-state-badge">캡처 프레임</div>
              )}
              <div className="face-guide" data-step={selectedStep.id}>
                <span />
              </div>
              <RuntimeOverlay stepId={selectedStep.id} provider={selectedProvider} />
            </div>
            <div className="wizard-sheet">
              <StepContent
                step={selectedStep}
                selectedProvider={selectedProvider}
                candidates={candidates}
                canBack={selectedStep.index > 0}
                onBack={goBack}
                onNext={goNext}
                onSelectProvider={setSelectedProvider}
              />
            </div>
          </div>
        </section>

        <aside className="wizard-debug-sheet">
          <div className="step-heading">
            <span>Debug sheet</span>
            <h2>얼굴 중앙 밖 evidence</h2>
          </div>
          <div className="debug-kv-list">
            <div>
              <span>captureSetId</span>
              <strong>preview-capture-set-v0</strong>
            </div>
            <div>
              <span>providers</span>
              <strong>{providerLabels[selectedProvider]} 선택</strong>
            </div>
            <div>
              <span>blendshapeAssist</span>
              <strong>off / on 비교</strong>
            </div>
            <div>
              <span>privacy</span>
              <strong>localOnly / no upload</strong>
            </div>
            <div>
              <span>build</span>
              <strong>Xcode pending</strong>
            </div>
          </div>
        </aside>
      </section>
    </main>
  );
}

function RuntimeOverlay({
  stepId,
  provider,
}: {
  stepId: WizardStepId;
  provider: ExtractionProvider;
}) {
  const previewUrl = getProviderPreview(provider);

  if (stepId === 'extract') {
    return (
      <div className="mesh-preview">
        <img src={MESH_OVERLAY_URL} alt="ARFace projection reference" />
      </div>
    );
  }

  if (stepId === 'adjust') {
    return (
      <div className="adjust-face-preview">
        <img src={previewUrl} alt="large generated lip adjustment preview" />
      </div>
    );
  }

  if (stepId === 'compare' || stepId === 'save') {
    return (
      <div className="lip-preview-mark">
        <img src={previewUrl} alt="generated lip preview" />
      </div>
    );
  }

  if (stepId === 'runtime') {
    return (
      <div className="lip-preview-mark runtime">
        <img src={ROUND_TRIP_URL} alt="round trip preview" />
      </div>
    );
  }

  return null;
}

function StepContent({
  step,
  selectedProvider,
  candidates,
  canBack,
  onBack,
  onNext,
  onSelectProvider,
}: {
  step: WizardStep;
  selectedProvider: ExtractionProvider;
  candidates: CandidatePreview[];
  canBack: boolean;
  onBack: () => void;
  onNext: () => void;
  onSelectProvider: (provider: ExtractionProvider) => void;
}) {
  switch (step.id) {
    case 'start':
      return <StartStep step={step} onNext={onNext} />;
    case 'align':
      return <AlignStep step={step} canBack={canBack} onBack={onBack} onNext={onNext} />;
    case 'capture':
      return <CaptureStep step={step} canBack={canBack} onBack={onBack} onNext={onNext} />;
    case 'extract':
      return (
        <ExtractStep
          step={step}
          selectedProvider={selectedProvider}
          canBack={canBack}
          onBack={onBack}
          onNext={onNext}
          onSelectProvider={onSelectProvider}
        />
      );
    case 'compare':
      return (
        <CompareStep
          step={step}
          candidates={candidates}
          selectedProvider={selectedProvider}
          canBack={canBack}
          onBack={onBack}
          onNext={onNext}
        />
      );
    case 'adjust':
      return <AdjustStep step={step} canBack={canBack} onBack={onBack} onNext={onNext} />;
    case 'save':
      return <SaveStep step={step} canBack={canBack} onBack={onBack} onNext={onNext} />;
    case 'runtime':
      return <RuntimeStep step={step} canBack={canBack} onBack={onBack} />;
    default:
      return null;
  }
}

function SheetHeader({
  step,
  canBack = false,
  onBack,
}: {
  step: WizardStep;
  canBack?: boolean;
  onBack?: () => void;
}) {
  return (
    <header className="sheet-header">
      <button
        type="button"
        className="sheet-back"
        disabled={!canBack}
        onClick={onBack}
      >
        이전
      </button>
      <div>
        <span className="eyebrow">Step {step.index + 1}</span>
        <h2>{step.title}</h2>
      </div>
      <strong>{step.state === 'locked' ? '대기' : step.state === 'active' ? '진행 중' : '완료'}</strong>
    </header>
  );
}

function StartStep({ step, onNext }: { step: WizardStep; onNext: () => void }) {
  return (
    <>
      <SheetHeader step={step} />
      <div className="permission-grid">
        <GatePill label="카메라" value="준비됨" />
        <GatePill label="ARKit" value="지원됨" />
        <GatePill label="처리 위치" value="기기 내부" />
      </div>
      <div className="sheet-actions">
        <button type="button" className="primary" onClick={onNext}>
          시작
        </button>
      </div>
    </>
  );
}

function AlignStep({
  step,
  canBack,
  onBack,
  onNext,
}: {
  step: WizardStep;
  canBack: boolean;
  onBack: () => void;
  onNext: () => void;
}) {
  return (
    <>
      <SheetHeader step={step} canBack={canBack} onBack={onBack} />
      <div className="quality-grid">
        <GatePill label="거리" value="좋음" />
        <GatePill label="밝기" value="좋음" />
        <GatePill label="흔들림" value="낮음" />
        <GatePill label="각도" value="정면" />
      </div>
      <div className="sheet-actions">
        <button type="button" onClick={onBack}>이전</button>
        <button type="button" className="primary" onClick={onNext}>
          촬영으로
        </button>
      </div>
    </>
  );
}

function CaptureStep({
  step,
  canBack,
  onBack,
  onNext,
}: {
  step: WizardStep;
  canBack: boolean;
  onBack: () => void;
  onNext: () => void;
}) {
  return (
    <>
      <SheetHeader step={step} canBack={canBack} onBack={onBack} />
      <div className="capture-progress">
        {captureShots.map(shot => (
          <div className="capture-shot" data-state={shot.state} key={shot.label}>
            <strong>{shot.label}</strong>
            <span>{shot.detail}</span>
          </div>
        ))}
      </div>
      <div className="sheet-actions">
        <button type="button" onClick={onBack}>이전</button>
        <button type="button" className="primary" onClick={onNext}>
          촬영 완료
        </button>
      </div>
    </>
  );
}

function ExtractStep({
  step,
  selectedProvider,
  canBack,
  onBack,
  onNext,
  onSelectProvider,
}: {
  step: WizardStep;
  selectedProvider: ExtractionProvider;
  canBack: boolean;
  onBack: () => void;
  onNext: () => void;
  onSelectProvider: (provider: ExtractionProvider) => void;
}) {
  return (
    <>
      <SheetHeader step={step} canBack={canBack} onBack={onBack} />
      <div className="provider-grid">
        <ProviderCard
          title="Vision"
          status="current-frame ready"
          selected={selectedProvider === 'vision'}
          onSelect={() => onSelectProvider('vision')}
        />
        <ProviderCard
          title="MediaPipe"
          status="current-frame ready"
          selected={selectedProvider === 'mediapipe'}
          onSelect={() => onSelectProvider('mediapipe')}
        />
      </div>
      <p className="sheet-note">
        이 단계에서는 둘 중 하나만 추출합니다. 비교 단계는 선택한 추출 결과에서 여러 후보를 봅니다.
      </p>
      <div className="sheet-actions">
        <button type="button" onClick={onBack}>이전</button>
        <button type="button" className="primary" onClick={onNext}>
          {providerLabels[selectedProvider]} 추출
        </button>
      </div>
    </>
  );
}

function CompareStep({
  step,
  candidates,
  selectedProvider,
  canBack,
  onBack,
  onNext,
}: {
  step: WizardStep;
  candidates: CandidatePreview[];
  selectedProvider: ExtractionProvider;
  canBack: boolean;
  onBack: () => void;
  onNext: () => void;
}) {
  return (
    <>
      <SheetHeader step={step} canBack={canBack} onBack={onBack} />
      <p className="sheet-note">
        추출 방식: {providerLabels[selectedProvider]}. 같은 경계에서 assist/off와 edge 후보를 비교합니다.
      </p>
      <div className="candidate-strip">
        {candidates.map(candidate => (
          <article className="candidate-tile" key={candidate.id}>
            <img src={candidate.src} alt={candidate.title} />
            <strong>{candidate.title}</strong>
            <span>{candidate.status}</span>
          </article>
        ))}
      </div>
      <div className="sheet-actions">
        <button type="button" onClick={onBack}>이전</button>
        <button type="button" className="primary" onClick={onNext}>
          선택
        </button>
      </div>
    </>
  );
}

function AdjustStep({
  step,
  canBack,
  onBack,
  onNext,
}: {
  step: WizardStep;
  canBack: boolean;
  onBack: () => void;
  onNext: () => void;
}) {
  return (
    <>
      <SheetHeader step={step} canBack={canBack} onBack={onBack} />
      <p className="sheet-note">
        위 캡처 프레임에 마스크를 크게 올려 보고 조정합니다. live camera 판단 화면이 아닙니다.
      </p>
      <div className="adjust-chip-grid">
        <button type="button">입꼬리 더 포함</button>
        <button type="button">아랫입술 줄이기</button>
        <button type="button">윗입술 조이기</button>
        <button type="button">조금 위로</button>
      </div>
      <div className="adjust-meter-list">
        <AdjustMeter label="입꼬리" value="0.30" />
        <AdjustMeter label="윗입술" value="-0.20" />
        <AdjustMeter label="아랫입술" value="0.15" />
        <AdjustMeter label="세로 위치" value="-0.10" />
      </div>
      <div className="stale-badge">변경 후 다시 생성 필요</div>
      <div className="sheet-actions">
        <button type="button" onClick={onBack}>이전</button>
        <button type="button" className="primary" onClick={onNext}>
          저장으로
        </button>
      </div>
    </>
  );
}

function SaveStep({
  step,
  canBack,
  onBack,
  onNext,
}: {
  step: WizardStep;
  canBack: boolean;
  onBack: () => void;
  onNext: () => void;
}) {
  return (
    <>
      <SheetHeader step={step} canBack={canBack} onBack={onBack} />
      <div className="package-summary">
        <GatePill label="captureSetId" value="포함" />
        <GatePill label="providerResults" value="포함" />
        <GatePill label="adjustment" value="포함" />
        <GatePill label="privacy" value="local-only" />
      </div>
      <div className="sheet-actions">
        <button type="button" onClick={onBack}>다시 조정</button>
        <button type="button" className="primary" onClick={onNext}>
          저장
        </button>
      </div>
    </>
  );
}

function RuntimeStep({
  step,
  canBack,
  onBack,
}: {
  step: WizardStep;
  canBack: boolean;
  onBack: () => void;
}) {
  return (
    <>
      <SheetHeader step={step} canBack={canBack} onBack={onBack} />
      <div className="runtime-ready-panel">
        <strong>Unity package smoke 준비</strong>
        <span>dynamic texture register / saved package parse / assist payload</span>
      </div>
      <div className="sheet-actions">
        <button type="button" onClick={onBack}>이전</button>
        <button type="button" className="primary">
          AR로 보기
        </button>
      </div>
    </>
  );
}

function GatePill({ label, value }: { label: string; value: string }) {
  return (
    <div className="gate-pill">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function ProviderCard({
  title,
  status,
  selected,
  onSelect,
}: {
  title: string;
  status: string;
  selected: boolean;
  onSelect: () => void;
}) {
  return (
    <button
      type="button"
      className="provider-card"
      data-selected={selected}
      onClick={onSelect}
    >
      <strong>{title}</strong>
      <span>{status}</span>
      <small>{selected ? '선택됨' : '선택 가능'} · fixture replay 금지</small>
    </button>
  );
}

function AdjustMeter({ label, value }: { label: string; value: string }) {
  return (
    <div className="adjust-meter">
      <span>{label}</span>
      <div>
        <i />
      </div>
      <strong>{value}</strong>
    </div>
  );
}
