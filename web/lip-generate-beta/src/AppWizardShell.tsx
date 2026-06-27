import { useMemo, useState } from 'react';

type WizardStepId =
  | 'start'
  | 'align'
  | 'capture'
  | 'extract'
  | 'blend'
  | 'adjust'
  | 'apply';

type CaptureShotState = 'pending' | 'next' | 'captured';

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

type RequiredCaptureShot = {
  id: string;
  label: string;
  guidance: string;
};

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
    id: 'blend',
    index: 4,
    title: '블렌딩 선택',
    subtitle: '기본 / 표정 보정 선택',
    gate: 'assist off/on candidates',
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
    id: 'apply',
    index: 6,
    title: 'AR 실행',
    subtitle: '저장하고 Unity 적용',
    gate: 'save / payload / ack',
    state: 'locked',
  },
];

const requiredCaptureShots: RequiredCaptureShot[] = [
  {
    id: 'neutral',
    label: '정면 기준',
    guidance: '입에 힘 빼고 정면',
  },
  {
    id: 'mouth-open',
    label: '살짝 벌림',
    guidance: '입 안쪽 분리 확인',
  },
  {
    id: 'smile',
    label: '미소',
    guidance: '입꼬리 확장 확인',
  },
  {
    id: 'pucker',
    label: '오므림',
    guidance: '중앙 압축 확인',
  },
  {
    id: 'yaw-left',
    label: '왼쪽 각도',
    guidance: '가림/투영 안정성',
  },
  {
    id: 'yaw-right',
    label: '오른쪽 각도',
    guidance: '가림/투영 안정성',
  },
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
      title: '기본 블렌딩',
      status: `${providerLabel} · assist off`,
      src,
    },
    {
      id: `${provider}-blend`,
      title: '표정 보정',
      status: `${providerLabel} · assist on`,
      src,
    },
    {
      id: `${provider}-soft`,
      title: '부드럽게',
      status: `${providerLabel} · edge feather`,
      src,
    },
    {
      id: `${provider}-safe`,
      title: '번짐 안전',
      status: `${providerLabel} · spill guard`,
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
  const [capturedShotCount, setCapturedShotCount] = useState(0);
  const [selectedCandidateId, setSelectedCandidateId] = useState('vision-off');
  const [applyState, setApplyState] = useState<'idle' | 'saving' | 'ack-wait'>(
    'idle',
  );
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
  const isCapturedFrameReview = selectedStep.index >= 3 || capturedShotCount > 0;
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
  const capturePrimaryAction = () => {
    if (capturedShotCount < requiredCaptureShots.length) {
      setCapturedShotCount(current =>
        Math.min(requiredCaptureShots.length, current + 1),
      );
      return;
    }

    goNext();
  };
  const startApply = () => {
    setApplyState('saving');
    window.setTimeout(() => {
      setApplyState('ack-wait');
      setMaxUnlockedIndex(current => Math.max(current, steps.length - 1));
      setSelectedStepId('apply');
    }, 350);
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
              data-mode={isCapturedFrameReview ? 'captured' : 'live'}
            >
              <img src={FACE_FRAME_URL} alt="capture reference frame" />
              {isCapturedFrameReview && (
                <div className="camera-state-badge">
                  저장된 캡처 프레임
                </div>
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
                selectedCandidateId={selectedCandidateId}
                capturedShotCount={capturedShotCount}
                applyState={applyState}
                canBack={selectedStep.index > 0}
                onBack={goBack}
                onNext={goNext}
                onCapturePrimary={capturePrimaryAction}
                onSelectProvider={setSelectedProvider}
                onSelectCandidate={setSelectedCandidateId}
                onApply={startApply}
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
              <strong>블렌딩 선택에서 off / on 결정</strong>
            </div>
            <div>
              <span>privacy</span>
              <strong>localOnly / no upload</strong>
            </div>
            <div>
              <span>build</span>
              <strong>Xcode build pending</strong>
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

  if (stepId === 'blend') {
    return (
      <div className="lip-preview-mark">
        <img src={previewUrl} alt="generated lip preview" />
      </div>
    );
  }

  if (stepId === 'apply') {
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
  selectedCandidateId,
  capturedShotCount,
  applyState,
  canBack,
  onBack,
  onNext,
  onCapturePrimary,
  onSelectProvider,
  onSelectCandidate,
  onApply,
}: {
  step: WizardStep;
  selectedProvider: ExtractionProvider;
  candidates: CandidatePreview[];
  selectedCandidateId: string;
  capturedShotCount: number;
  applyState: 'idle' | 'saving' | 'ack-wait';
  canBack: boolean;
  onBack: () => void;
  onNext: () => void;
  onCapturePrimary: () => void;
  onSelectProvider: (provider: ExtractionProvider) => void;
  onSelectCandidate: (candidateId: string) => void;
  onApply: () => void;
}) {
  switch (step.id) {
    case 'start':
      return <StartStep step={step} onNext={onNext} />;
    case 'align':
      return <AlignStep step={step} canBack={canBack} onBack={onBack} onNext={onNext} />;
    case 'capture':
      return (
        <CaptureStep
          step={step}
          capturedShotCount={capturedShotCount}
          canBack={canBack}
          onBack={onBack}
          onPrimary={onCapturePrimary}
        />
      );
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
    case 'blend':
      return (
        <BlendStep
          step={step}
          candidates={candidates}
          selectedCandidateId={selectedCandidateId}
          selectedProvider={selectedProvider}
          canBack={canBack}
          onBack={onBack}
          onNext={onNext}
          onSelectCandidate={onSelectCandidate}
        />
      );
    case 'adjust':
      return (
        <AdjustStep
          step={step}
          canBack={canBack}
          onBack={onBack}
          onApply={onApply}
        />
      );
    case 'apply':
      return (
        <ApplyStep
          step={step}
          applyState={applyState}
          canBack={canBack}
          onBack={onBack}
        />
      );
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
  capturedShotCount,
  canBack,
  onBack,
  onPrimary,
}: {
  step: WizardStep;
  capturedShotCount: number;
  canBack: boolean;
  onBack: () => void;
  onPrimary: () => void;
}) {
  const isComplete = capturedShotCount >= requiredCaptureShots.length;
  const nextShot = requiredCaptureShots[capturedShotCount];

  return (
    <>
      <SheetHeader step={step} canBack={canBack} onBack={onBack} />
      <p className="sheet-note">
        촬영 버튼은 하나만 둡니다. 앱이 필요한 표정 큐를 순서대로 안내하고,
        완료된 순간 저장된 frame review로 넘어갑니다.
      </p>
      <div className="capture-progress">
        {requiredCaptureShots.map((shot, index) => {
          const state: CaptureShotState =
            index < capturedShotCount
              ? 'captured'
              : index === capturedShotCount
                ? 'next'
                : 'pending';

          return (
          <div className="capture-shot" data-state={state} key={shot.id}>
            <strong>{shot.label}</strong>
            <span>
              {state === 'captured'
                ? '촬영됨'
                : state === 'next'
                  ? shot.guidance
                  : '대기'}
            </span>
          </div>
          );
        })}
      </div>
      {capturedShotCount > 0 && (
        <div className="capture-feedback">
          <strong>촬영 저장됨</strong>
          <span>{capturedShotCount}/{requiredCaptureShots.length} 컷 완료</span>
        </div>
      )}
      <div className="sheet-actions">
        <button type="button" onClick={onBack}>이전</button>
        <button type="button" className="primary" onClick={onPrimary}>
          {isComplete ? '추출 단계로 이동' : `${nextShot?.label ?? '다음'} 촬영`}
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

function BlendStep({
  step,
  candidates,
  selectedCandidateId,
  selectedProvider,
  canBack,
  onBack,
  onNext,
  onSelectCandidate,
}: {
  step: WizardStep;
  candidates: CandidatePreview[];
  selectedCandidateId: string;
  selectedProvider: ExtractionProvider;
  canBack: boolean;
  onBack: () => void;
  onNext: () => void;
  onSelectCandidate: (candidateId: string) => void;
}) {
  return (
    <>
      <SheetHeader step={step} canBack={canBack} onBack={onBack} />
      <p className="sheet-note">
        추출 방식은 {providerLabels[selectedProvider]} 하나입니다. 여기서는 같은
        경계에서 기본/표정 보정/부드러운 경계 후보를 고릅니다.
      </p>
      <div className="candidate-strip">
        {candidates.map(candidate => (
          <button
            type="button"
            className="candidate-tile"
            data-selected={candidate.id === selectedCandidateId}
            key={candidate.id}
            onClick={() => onSelectCandidate(candidate.id)}
          >
            <img src={candidate.src} alt={candidate.title} />
            <strong>{candidate.title}</strong>
            <span>{candidate.status}</span>
          </button>
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
  onApply,
}: {
  step: WizardStep;
  canBack: boolean;
  onBack: () => void;
  onApply: () => void;
}) {
  return (
    <>
      <SheetHeader step={step} canBack={canBack} onBack={onBack} />
      <p className="sheet-note">
        입술만 잘라 보지 않습니다. 전체 얼굴 캡처 위에서 현재 마스크가 보이는
        상태로 조정하고, 변경값은 즉시 package preview에 반영됩니다.
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
      <div className="stale-badge">변경 즉시 현재 후보에 반영</div>
      <div className="sheet-actions">
        <button type="button" onClick={onBack}>이전</button>
        <button type="button" className="primary" onClick={onApply}>
          저장하고 AR 실행
        </button>
      </div>
    </>
  );
}

function ApplyStep({
  step,
  applyState,
  canBack,
  onBack,
}: {
  step: WizardStep;
  applyState: 'idle' | 'saving' | 'ack-wait';
  canBack: boolean;
  onBack: () => void;
}) {
  return (
    <>
      <SheetHeader step={step} canBack={canBack} onBack={onBack} />
      <div className="runtime-ready-panel">
        <strong>
          {applyState === 'saving'
            ? 'local-only 저장 중'
            : applyState === 'ack-wait'
              ? 'Unity 적용 ack 대기'
              : '저장하고 AR 실행 준비'}
        </strong>
        <span>
          saveGeneratedPackage {'->'} ApplyGeneratedLipMaskJson {'->'} generated_lip_mask_applied
        </span>
      </div>
      <div className="package-summary">
        <GatePill label="save" value={applyState === 'idle' ? '대기' : '완료'} />
        <GatePill label="payload" value={applyState === 'idle' ? '대기' : '전송'} />
        <GatePill label="Unity ack" value={applyState === 'ack-wait' ? '대기 중' : '필수'} />
        <GatePill label="AR 화면" value="ack 후 전환" />
      </div>
      <div className="sheet-actions">
        <button type="button" onClick={onBack}>이전</button>
        <button type="button" className="primary" disabled>
          Xcode 빌드에서 확인
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
