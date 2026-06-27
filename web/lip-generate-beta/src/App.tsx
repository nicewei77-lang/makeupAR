import { useEffect, useMemo, useReducer, useState } from 'react';
import {
  buildUnityMessageFromPackage,
  ExpressionAssistMode,
  LipAdjustment,
  LipBoundary2D,
  LipGenerateState,
  LipMaskProvider,
  INITIAL_LIP_GENERATE_STATE,
  lipGenerateReducer,
} from '../../../packages/lip-generate-core/src';
import {
  adjustLipBoundaryFromPrevious,
  buildLipBoundarySvgPath,
} from '../../../packages/lip-generate-core/src/lipBoundaryAdjustment';
import {
  LipGenerateFixture,
  LipGenerateFixtureInventory,
} from '../../../packages/lip-generate-core/src/fixtureInventory';
import {
  artifactUrl,
  buildGenerateRequest,
  defaultAdjustment,
  fetchSavedPackages,
  fetchFixtures,
  fixtureLabel,
  generateLipMask,
  saveGeneratedPackage,
  SavedLipPackageRecord,
  ServerGenerateResult,
} from './localServerClient';
import { AppWizardShell } from './AppWizardShell';
import { FullFaceRegionShell } from './FullFaceRegionShell';

const ADJUSTMENT_FIELDS: Array<keyof LipAdjustment> = [
  'cornerReach',
  'upperLipTightness',
  'lowerLipTightness',
  'verticalOffset',
];

const FOUR_WAY: Array<{
  provider: LipMaskProvider;
  expressionMode: ExpressionAssistMode;
  label: string;
}> = [
  { provider: 'vision', expressionMode: 'uvOnly', label: 'Vision · 기본 적용' },
  {
    provider: 'vision',
    expressionMode: 'blendshapeAssist',
    label: 'Vision · 표정 보정',
  },
  { provider: 'mediapipe', expressionMode: 'uvOnly', label: 'MediaPipe · 기본 적용' },
  {
    provider: 'mediapipe',
    expressionMode: 'blendshapeAssist',
    label: 'MediaPipe · 표정 보정',
  },
];

const PROVIDER_LABELS: Record<LipMaskProvider, string> = {
  vision: 'Vision 경계',
  mediapipe: 'MediaPipe 경계',
};

const EXPRESSION_LABELS: Record<ExpressionAssistMode, string> = {
  uvOnly: '기본 적용',
  blendshapeAssist: '표정 보정',
};

const ADJUSTMENT_LABELS: Record<keyof LipAdjustment, string> = {
  cornerReach: '입꼬리 포함',
  upperLipTightness: '윗입술 조임',
  lowerLipTightness: '아랫입술 조임',
  verticalOffset: '세로 위치',
};

const ADJUSTMENT_STEP = 0.05;

type StatusTone = 'neutral' | 'warn' | 'bad';

function App() {
  const [mode, setMode] = useState<'appShell' | 'fullFace' | 'lipBeta'>(
    'appShell',
  );
  const [state, dispatch] = useReducer(
    lipGenerateReducer,
    INITIAL_LIP_GENERATE_STATE,
  );
  const [inventory, setInventory] = useState<LipGenerateFixtureInventory | null>(
    null,
  );
  const [statusMessage, setStatusMessage] = useState('로컬 서버 연결 대기 중');
  const [statusTone, setStatusTone] = useState<StatusTone>('neutral');
  const [compareResults, setCompareResults] = useState<ServerGenerateResult[]>([]);
  const [savedRecords, setSavedRecords] = useState<SavedLipPackageRecord[]>([]);
  const [saveMessage, setSaveMessage] = useState('저장된 패키지 없음');
  const [isBusy, setIsBusy] = useState(false);

  const fixtures = inventory?.fixtures ?? [];
  const selectedFixture = useMemo(
    () =>
      fixtures.find(fixture => fixture.fixtureId === state.selectedFixtureId) ??
      fixtures[0],
    [fixtures, state.selectedFixtureId],
  );

  const currentRequest = useMemo(
    () =>
      buildGenerateRequest({
        provider: state.provider,
        expressionMode: state.expressionMode,
        adjustment: state.adjustment,
        fixtureId: state.selectedFixtureId ?? inventory?.defaultFixtureId ?? '',
      }),
    [
      inventory?.defaultFixtureId,
      state.adjustment,
      state.expressionMode,
      state.provider,
      state.selectedFixtureId,
    ],
  );

  useEffect(() => {
    if (mode !== 'lipBeta') {
      return;
    }
    void refreshFixtures();
    void refreshSavedPackages();
  }, [mode]);

  async function refreshFixtures() {
    setStatusMessage('로컬 fixture 확인 중');
    setStatusTone('neutral');
    const nextInventory = await fetchFixtures();
    setInventory(nextInventory);
    dispatch({
      type: 'selectFixture',
      fixtureId: nextInventory.defaultFixtureId,
    });
    setStatusMessage('로컬 fixture 준비 완료');
  }

  async function refreshSavedPackages() {
    try {
      const records = await fetchSavedPackages();
      setSavedRecords(records);
      setSaveMessage(
        records.length
          ? `${records.length}개 패키지 저장됨`
          : '저장된 패키지 없음',
      );
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      setSaveMessage(`저장 목록 확인 실패: ${message}`);
    }
  }

  async function generateSelected() {
    setIsBusy(true);
    setStatusMessage('마스크 생성 및 UV round-trip 실행 중');
    setStatusTone('neutral');
    dispatch({ type: 'startGenerate' });
    try {
      const result = await generateLipMask(currentRequest);
      dispatch({ type: 'completeGenerate', result });
      setStatusMessage(buildStatusMessage(result));
      setStatusTone(result.status === 'blocked' ? 'bad' : 'warn');
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      dispatch({ type: 'blockGenerate', blockedReason: message });
      setStatusMessage(message);
      setStatusTone('bad');
    } finally {
      setIsBusy(false);
    }
  }

  async function generateFourWay() {
    if (!state.selectedFixtureId) {
      return;
    }
    setIsBusy(true);
    setStatusMessage('4-Way 비교 생성 중');
    setStatusTone('neutral');
    const results: ServerGenerateResult[] = [];
    try {
      for (const combo of FOUR_WAY) {
        const request = buildGenerateRequest({
          provider: combo.provider,
          expressionMode: combo.expressionMode,
          adjustment: state.adjustment,
          fixtureId: state.selectedFixtureId,
        });
        results.push(await generateLipMask(request));
      }
      setCompareResults(results);
      dispatch({ type: 'completeGenerate', result: results[0] });
      setStatusMessage('4가지 후보 생성 완료 · iPhone 적용 검증 전');
      setStatusTone('warn');
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      dispatch({ type: 'blockGenerate', blockedReason: message });
      setStatusMessage(message);
      setStatusTone('bad');
    } finally {
      setIsBusy(false);
    }
  }

  async function saveCurrentResult() {
    if (!lastResult) {
      setSaveMessage('먼저 입술 마스크를 생성해야 저장할 수 있습니다.');
      return;
    }
    setIsBusy(true);
    setSaveMessage(
      isLastResultCurrent
        ? '선택 패키지 저장 중'
        : '최신 조정값 package 갱신 후 저장 중',
    );
    try {
      let resultToSave = lastResult;
      if (!isLastResultCurrent) {
        resultToSave = await generateLipMask(currentRequest);
        dispatch({ type: 'completeGenerate', result: resultToSave });
        setCompareResults([]);
      }
      const record = await saveGeneratedPackage(resultToSave);
      setSavedRecords(previous => [
        record,
        ...previous.filter(
          item => item.generatedMaskId !== record.generatedMaskId,
        ),
      ]);
      setSaveMessage('선택 패키지 저장 완료 · local-only');
      setStatusMessage('조정 결과 저장 완료 · iPhone 적용 검증 전');
      setStatusTone('warn');
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      setSaveMessage(`저장 실패: ${message}`);
      setStatusTone('bad');
    } finally {
      setIsBusy(false);
    }
  }

  const lastResult = state.lastResult as ServerGenerateResult | undefined;
  const lastPackage = lastResult?.package;
  const isLastResultCurrent = isGeneratedForCurrentControls(lastResult, state);
  const warnings = lastResult?.warnings ?? state.warnings;
  const livePreviewBoundary = useMemo(() => {
    if (!lastPackage?.lipBoundary2D) {
      return undefined;
    }
    return adjustLipBoundaryFromPrevious(
      lastPackage.lipBoundary2D,
      lastPackage.adjustment,
      state.adjustment,
      frameSizeFromPackage(lastPackage),
    );
  }, [lastPackage, state.adjustment]);
  const payloadPreview = {
    request: currentRequest,
    lastPackage: compactPayloadForDisplay(lastPackage ?? null),
    unityMessagePreview: compactPayloadForDisplay(
      lastPackage ? buildUnityMessageFromPackage(lastPackage) : null,
    ),
  };

  if (mode === 'appShell') {
    return (
      <AppWizardShell
        onOpenFullFace={() => setMode('fullFace')}
        onOpenLipBeta={() => setMode('lipBeta')}
      />
    );
  }

  if (mode === 'fullFace') {
    return (
      <FullFaceRegionShell
        onOpenAppShell={() => setMode('appShell')}
        onOpenLipBeta={() => setMode('lipBeta')}
      />
    );
  }

  return (
    <main className="app-shell">
      <header className="toolbar">
        <div>
          <h1>입술 맞춤 Generate Beta</h1>
          <p className="status-line" data-tone={statusTone}>
            {statusMessage}
          </p>
        </div>
        <div className="toolbar-actions">
          <button type="button" onClick={() => setMode('fullFace')}>
            Full-face package
          </button>
          <button type="button" onClick={() => setMode('appShell')}>
            App shell
          </button>
          <button type="button" onClick={() => void refreshFixtures()}>
            샘플 새로고침
          </button>
          <button
            type="button"
            className="primary"
            onClick={() => void generateSelected()}
            disabled={isBusy || !selectedFixture}
          >
            입술 마스크 생성
          </button>
          <button
            type="button"
            onClick={() => void generateFourWay()}
            disabled={isBusy || !selectedFixture}
          >
            4가지 후보 비교
          </button>
        </div>
      </header>

      <section className="workspace">
        <aside className="control-panel">
          <section className="panel-section">
            <div className="step-heading">
              <span>Step 1</span>
              <h2>입력 선택</h2>
            </div>
            <label>
              샘플 얼굴
              <select
                value={state.selectedFixtureId ?? ''}
                onChange={event =>
                  dispatch({
                    type: 'selectFixture',
                    fixtureId: event.currentTarget.value,
                  })
                }
              >
                {fixtures.map(fixture => (
                  <option key={fixture.fixtureId} value={fixture.fixtureId}>
                    {fixtureLabel(fixture)}
                  </option>
                ))}
              </select>
            </label>
            <label>
              생성 방식
              <select
                value={state.provider}
                onChange={event =>
                  dispatch({
                    type: 'selectProvider',
                    provider: event.currentTarget.value as LipMaskProvider,
                  })
                }
              >
                <option value="vision">{PROVIDER_LABELS.vision}</option>
                <option value="mediapipe">{PROVIDER_LABELS.mediapipe}</option>
              </select>
            </label>
            <label>
              표정 보정
              <select
                value={state.expressionMode}
                onChange={event =>
                  dispatch({
                    type: 'selectExpressionMode',
                    expressionMode: event.currentTarget
                      .value as ExpressionAssistMode,
                  })
                }
              >
                <option value="uvOnly">{EXPRESSION_LABELS.uvOnly}</option>
                <option value="blendshapeAssist">
                  {EXPRESSION_LABELS.blendshapeAssist}
                </option>
              </select>
            </label>
          </section>

          <AdjustmentPanel
            adjustment={state.adjustment}
            onReset={() => {
              for (const key of ADJUSTMENT_FIELDS) {
                dispatch({
                  type: 'setAdjustment',
                  key,
                  value: defaultAdjustment()[key],
                });
              }
            }}
            onChange={(key, value) =>
              dispatch({ type: 'setAdjustment', key, value })
            }
          />

          <section className="panel-section">
            <div className="step-heading">
              <span>Step 4</span>
              <h2>검증 체크</h2>
            </div>
            <GateList result={lastResult} fallbackStatus={state.status} />
          </section>
        </aside>

        <section className="inspect-panel">
          <ResultSummary
            result={lastResult}
            isBusy={isBusy}
            isStale={Boolean(lastResult && !isLastResultCurrent)}
          />
          {lastResult && !isLastResultCurrent ? (
            <section className="stale-callout">
              <strong>사진 preview는 즉시 반영 중입니다.</strong>
              <span>
                저장을 누르면 현재 조정값으로 package를 갱신한 뒤 local-only로
                저장합니다.
              </span>
            </section>
          ) : null}
          <PreviewGrid
            fixture={selectedFixture}
            result={lastResult}
            livePreviewBoundary={livePreviewBoundary}
          />
          <CompareGrid results={compareResults} />
          <SavePanel
            result={lastResult}
            isBusy={isBusy}
            message={saveMessage}
            records={savedRecords}
            onSave={() => void saveCurrentResult()}
          />
          <PayloadPanel payload={payloadPreview} />
          <WarningsPanel warnings={warnings} />
        </section>
      </section>
    </main>
  );
}

function ResultSummary({
  result,
  isBusy,
  isStale,
}: {
  result?: ServerGenerateResult;
  isBusy: boolean;
  isStale: boolean;
}) {
  const title = isBusy
    ? '생성 중'
    : isStale
      ? '프리뷰 즉시 반영'
      : result
        ? buildStatusTitle(result)
        : '생성 대기';
  const details = result
    ? [
        `${PROVIDER_LABELS[result.provider]}`,
        `${EXPRESSION_LABELS[result.expressionMode]}`,
        isStale ? '저장 시 package 갱신' : '현재 조정값 반영됨',
        result.runtimeApplyReady ? 'Unity 적용 완료' : 'iPhone 적용 검증 전',
      ]
    : ['로컬 fixture 준비', 'no upload', 'raw frame 장기 저장 없음'];

  return (
    <section
      className="result-summary"
      data-status={isStale ? 'stale' : (result?.status ?? 'ready')}
    >
      <div>
        <span className="eyebrow">Generate 상태</span>
        <h2>{title}</h2>
      </div>
      <div className="summary-chips">
        {details.map(detail => (
          <span key={detail}>{detail}</span>
        ))}
      </div>
    </section>
  );
}

function SavePanel({
  result,
  isBusy,
  message,
  records,
  onSave,
}: {
  result?: ServerGenerateResult;
  isBusy: boolean;
  message: string;
  records: SavedLipPackageRecord[];
  onSave: () => void;
}) {
  const canSave = Boolean(result?.package && result.runDirectory);

  return (
    <section className="save-section">
      <div className="section-heading">
        <div className="step-heading">
          <span>Step 5</span>
          <h2>선택 저장</h2>
        </div>
        <button
          type="button"
          className="primary"
          disabled={!canSave || isBusy}
          onClick={onSave}
        >
          현재 패키지 저장
        </button>
      </div>
      <p className="save-message">{message}</p>
      {!canSave ? (
        <p className="save-hint">
          Provider나 표정 보정을 바꾼 뒤에는 다시 Generate 해야 합니다. 조정값만
          바뀐 경우 저장 시 최신 package로 갱신됩니다.
        </p>
      ) : null}
      <div className="saved-list">
        {records.map(record => (
          <article className="saved-record" key={record.generatedMaskId}>
            <strong>{recordLabel(record)}</strong>
            <span>
              {formatAdjustment(record.adjustment)} ·{' '}
              {record.runtimeReady ? 'runtime ready' : 'iPhone 검증 전'}
            </span>
            <code>{record.packagePath}</code>
          </article>
        ))}
      </div>
    </section>
  );
}

function GateList({
  result,
  fallbackStatus,
}: {
  result?: ServerGenerateResult;
  fallbackStatus: string;
}) {
  const rows = [
    {
      label: '입력 선택',
      state: 'done',
      value: '완료',
    },
    {
      label: '입술 경계 생성',
      state: result?.maskOutputs?.mask ? 'done' : 'pending',
      value: result?.maskOutputs?.mask ? '완료' : '대기',
    },
    {
      label: 'ARFace UV 변환',
      state: result?.uvMaskReady ? 'done' : 'pending',
      value: result?.uvMaskReady ? '완료' : '대기',
    },
    {
      label: '되돌려보기',
      state: result?.roundTripReady ? 'done' : 'pending',
      value: result?.roundTripReady ? '완료' : '대기',
    },
    {
      label: 'Unity iPhone 적용',
      state: result?.runtimeApplyReady ? 'done' : 'blocked',
      value: result?.runtimeApplyReady ? '완료' : '검증 전',
    },
  ];

  return (
    <div className="gate-steps">
      <div className="gate-status">
        <span>현재 판정</span>
        <strong>{statusLabel(result?.status ?? fallbackStatus)}</strong>
      </div>
      {rows.map(row => (
        <div className="gate-step" data-state={row.state} key={row.label}>
          <span>{row.label}</span>
          <strong>{row.value}</strong>
        </div>
      ))}
    </div>
  );
}

function buildStatusMessage(result: ServerGenerateResult): string {
  if (result.status === 'blocked') {
    return `${PROVIDER_LABELS[result.provider]} 생성 중단 · 원인 확인 필요`;
  }
  return `${PROVIDER_LABELS[result.provider]} ${EXPRESSION_LABELS[result.expressionMode]} 생성 완료 · iPhone 적용 검증 전`;
}

function buildStatusTitle(result: ServerGenerateResult): string {
  if (result.status === 'blocked') {
    return '생성 중단';
  }
  if (result.runtimeApplyReady) {
    return '생성 및 적용 완료';
  }
  return '웹 생성 완료 · iPhone 적용 검증 전';
}

function statusLabel(status: string): string {
  switch (status) {
    case 'ready':
      return '준비됨';
    case 'partial':
      return '부분 완료';
    case 'blocked':
      return '중단';
    default:
      return status;
  }
}

function adjustmentEquals(a?: LipAdjustment, b?: LipAdjustment): boolean {
  if (!a || !b) {
    return false;
  }
  return ADJUSTMENT_FIELDS.every(key => Math.abs(a[key] - b[key]) < 0.001);
}

function isGeneratedForCurrentControls(
  result: ServerGenerateResult | undefined,
  state: LipGenerateState,
): boolean {
  if (!result?.package) {
    return false;
  }
  return (
    result.provider === state.provider &&
    result.expressionMode === state.expressionMode &&
    adjustmentEquals(result.package.adjustment, state.adjustment)
  );
}

function frameSizeFromPackage(packageData?: ServerGenerateResult['package']):
  | { width: number; height: number }
  | undefined {
  const width = packageData?.sourceFrameMetadata?.frameWidth;
  const height = packageData?.sourceFrameMetadata?.frameHeight;
  if (
    typeof width === 'number' &&
    typeof height === 'number' &&
    width > 0 &&
    height > 0
  ) {
    return { width, height };
  }
  return undefined;
}

function formatAdjustment(adjustment: LipAdjustment): string {
  return ADJUSTMENT_FIELDS.map(key => `${ADJUSTMENT_LABELS[key]} ${adjustment[key].toFixed(2)}`).join(
    ' / ',
  );
}

function recordLabel(record: SavedLipPackageRecord): string {
  return `${PROVIDER_LABELS[record.provider]} · ${EXPRESSION_LABELS[record.expressionMode]}`;
}

function AdjustmentPanel({
  adjustment,
  onChange,
  onReset,
}: {
  adjustment: LipAdjustment;
  onChange: (key: keyof LipAdjustment, value: number) => void;
  onReset: () => void;
}) {
  return (
    <section className="panel-section">
      <div className="section-heading compact">
        <div className="step-heading">
          <span>Step 2</span>
          <h2>미세 조정</h2>
        </div>
        <button type="button" onClick={onReset}>
          초기화
        </button>
      </div>
      <div className="range-stack">
        {ADJUSTMENT_FIELDS.map(key => (
          <div className="range-row" key={key}>
            <label htmlFor={`range-${key}`}>
              <span>{ADJUSTMENT_LABELS[key]}</span>
              <div className="range-control">
                <button
                  type="button"
                  aria-label={`${ADJUSTMENT_LABELS[key]} 줄이기`}
                  onClick={() => onChange(key, adjustment[key] - ADJUSTMENT_STEP)}
                >
                  -
                </button>
                <input
                  id={`range-${key}`}
                  aria-label={ADJUSTMENT_LABELS[key]}
                  type="range"
                  min="-1"
                  max="1"
                  step={ADJUSTMENT_STEP}
                  value={adjustment[key]}
                  onChange={event =>
                    onChange(key, Number(event.currentTarget.value))
                  }
                />
                <button
                  type="button"
                  aria-label={`${ADJUSTMENT_LABELS[key]} 늘리기`}
                  onClick={() => onChange(key, adjustment[key] + ADJUSTMENT_STEP)}
                >
                  +
                </button>
              </div>
            </label>
            <output htmlFor={`range-${key}`}>
              {adjustment[key].toFixed(2)}
            </output>
          </div>
        ))}
      </div>
    </section>
  );
}

function PreviewGrid({
  fixture,
  result,
  livePreviewBoundary,
}: {
  fixture?: LipGenerateFixture;
  result?: ServerGenerateResult;
  livePreviewBoundary?: LipBoundary2D;
}) {
  const frameSrc = artifactUrl(fixture?.framePath);
  const frameSize = frameSizeFromPackage(result?.package);

  return (
    <section className="preview-grid">
      <PreviewFigure title="원본 얼굴" src={frameSrc} />
      {livePreviewBoundary && frameSize ? (
        <BoundaryMaskFigure
          title="입술 경계 마스크"
          boundary={livePreviewBoundary}
          frameSize={frameSize}
        />
      ) : (
        <PreviewFigure
          title="입술 경계 마스크"
          src={artifactUrl(result?.maskOutputs?.mask)}
        />
      )}
      <PreviewFigure
        title="ARFace용 UV 마스크"
        src={artifactUrl(result?.package?.uvMaskTexture)}
      />
      {livePreviewBoundary && frameSrc && frameSize ? (
        <LiveAdjustedPreviewFigure
          title="되돌려보기"
          frameSrc={frameSrc}
          boundary={livePreviewBoundary}
          frameSize={frameSize}
        />
      ) : (
        <PreviewFigure
          title="되돌려보기"
          src={artifactUrl(result?.package?.roundTripPreview)}
        />
      )}
    </section>
  );
}

function PreviewFigure({ title, src }: { title: string; src: string }) {
  return (
    <figure>
      <figcaption>{title}</figcaption>
      {src ? <img src={src} alt={title} /> : <div className="image-empty" />}
    </figure>
  );
}

function BoundaryMaskFigure({
  title,
  boundary,
  frameSize,
}: {
  title: string;
  boundary: LipBoundary2D;
  frameSize: { width: number; height: number };
}) {
  const path = buildLipBoundarySvgPath(boundary);

  return (
    <figure>
      <figcaption>{title}</figcaption>
      <div className="boundary-mask-preview">
        <svg
          viewBox={`0 0 ${frameSize.width} ${frameSize.height}`}
          preserveAspectRatio="none"
          aria-label={title}
        >
          <path d={path} fill="#fff" fillRule="evenodd" />
        </svg>
      </div>
    </figure>
  );
}

function LiveAdjustedPreviewFigure({
  title,
  frameSrc,
  boundary,
  frameSize,
}: {
  title: string;
  frameSrc: string;
  boundary: LipBoundary2D;
  frameSize: { width: number; height: number };
}) {
  const path = buildLipBoundarySvgPath(boundary);

  return (
    <figure>
      <figcaption>{title}</figcaption>
      <div className="live-adjusted-preview">
        <img src={frameSrc} alt={title} />
        <svg
          viewBox={`0 0 ${frameSize.width} ${frameSize.height}`}
          preserveAspectRatio="none"
          aria-label="실시간 조정 마스크"
        >
          <path
            d={path}
            fill="rgba(217, 75, 116, 0.68)"
            fillRule="evenodd"
            stroke="rgba(255, 255, 255, 0.82)"
            strokeWidth="2"
          />
        </svg>
      </div>
    </figure>
  );
}

function CompareGrid({ results }: { results: ServerGenerateResult[] }) {
  return (
    <section className="compare-section">
      <div className="section-heading">
        <div className="step-heading">
          <span>Step 3</span>
          <h2>4가지 후보 비교</h2>
        </div>
        <span>Vision / MediaPipe x 기본 / 표정 보정</span>
      </div>
      <div className="compare-grid">
        {results.map(result => {
          const score = result.package?.uvCoverageMetadata?.roundTripScore;
          const label =
            FOUR_WAY.find(
              combo =>
                combo.provider === result.provider &&
                combo.expressionMode === result.expressionMode,
            )?.label ??
            `${PROVIDER_LABELS[result.provider]} · ${
              EXPRESSION_LABELS[result.expressionMode]
            }`;
          return (
            <article
              className="compare-card"
              key={`${result.provider}-${result.expressionMode}-${result.generatedMaskId}`}
            >
              <header>
                <strong>{label}</strong>
                <small>{statusLabel(result.status)}</small>
              </header>
              <img
                src={artifactUrl(result.package?.roundTripPreview)}
                alt={`${result.provider} ${result.expressionMode}`}
              />
              <header>
                <small>
                  IoU {score?.iou ?? '-'} · UV{' '}
                  {result.uvMaskReady ? '완료' : '대기'}
                </small>
              </header>
            </article>
          );
        })}
      </div>
    </section>
  );
}

function PayloadPanel({ payload }: { payload: unknown }) {
  return (
    <details className="payload-section debug-section">
      <summary>
        <strong>Debug payload</strong>
        <span>RN/Unity 전달값</span>
      </summary>
      <pre>{JSON.stringify(payload, null, 2)}</pre>
    </details>
  );
}

function compactPayloadForDisplay(value: unknown): unknown {
  if (Array.isArray(value)) {
    return value.map(item => compactPayloadForDisplay(item));
  }

  if (value && typeof value === 'object') {
    return Object.fromEntries(
      Object.entries(value).map(([key, entry]) => {
        if (
          (key === 'maskPngBase64' || key === 'maskRawRgbaBase64') &&
          typeof entry === 'string'
        ) {
          return [key, `[base64 ${entry.length} chars]`];
        }

        return [key, compactPayloadForDisplay(entry)];
      }),
    );
  }

  return value;
}

function WarningsPanel({ warnings }: { warnings: string[] }) {
  return (
    <section className="payload-section">
      <div className="section-heading">
        <h2>주의 항목</h2>
        <span>ready / partial / blocked 근거</span>
      </div>
      <ul className="warning-list">
        {warnings.map(warning => (
          <li key={warning}>{warning}</li>
        ))}
      </ul>
    </section>
  );
}

export default App;
