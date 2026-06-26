import { useEffect, useMemo, useReducer, useState } from 'react';
import {
  ExpressionAssistMode,
  LipAdjustment,
  LipMaskProvider,
  INITIAL_LIP_GENERATE_STATE,
  lipGenerateReducer,
} from '../../../packages/lip-generate-core/src';
import {
  LipGenerateFixture,
  LipGenerateFixtureInventory,
} from '../../../packages/lip-generate-core/src/fixtureInventory';
import {
  artifactUrl,
  buildGenerateRequest,
  defaultAdjustment,
  fetchFixtures,
  fixtureLabel,
  generateLipMask,
  ServerGenerateResult,
} from './localServerClient';

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
  { provider: 'vision', expressionMode: 'uvOnly', label: 'Vision / UV Only' },
  {
    provider: 'vision',
    expressionMode: 'blendshapeAssist',
    label: 'Vision / Blendshape Assist',
  },
  { provider: 'mediapipe', expressionMode: 'uvOnly', label: 'MediaPipe / UV Only' },
  {
    provider: 'mediapipe',
    expressionMode: 'blendshapeAssist',
    label: 'MediaPipe / Blendshape Assist',
  },
];

type StatusTone = 'neutral' | 'warn' | 'bad';

function App() {
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
    void refreshFixtures();
  }, []);

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

  async function generateSelected() {
    setIsBusy(true);
    setStatusMessage('마스크 생성 및 UV round-trip 실행 중');
    setStatusTone('neutral');
    dispatch({ type: 'startGenerate' });
    try {
      const result = await generateLipMask(currentRequest);
      dispatch({ type: 'completeGenerate', result });
      setStatusMessage(
        `${result.provider} ${result.expressionMode} 생성 완료: ${result.status}`,
      );
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
      setStatusMessage('4-Way 비교 생성 완료');
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

  const lastResult = state.lastResult as ServerGenerateResult | undefined;
  const lastPackage = lastResult?.package;
  const warnings = lastResult?.warnings ?? state.warnings;
  const payloadPreview = {
    request: currentRequest,
    lastPackage: lastPackage ?? null,
    unityMessagePreview: lastPackage?.runtimeApplyPayload ?? null,
  };

  return (
    <main className="app-shell">
      <header className="toolbar">
        <div>
          <h1>E7 Lip Generate Beta</h1>
          <p className="status-line" data-tone={statusTone}>
            {statusMessage}
          </p>
        </div>
        <div className="toolbar-actions">
          <button type="button" onClick={() => void refreshFixtures()}>
            Fixtures
          </button>
          <button
            type="button"
            className="primary"
            onClick={() => void generateSelected()}
            disabled={isBusy || !selectedFixture}
          >
            Generate
          </button>
          <button
            type="button"
            onClick={() => void generateFourWay()}
            disabled={isBusy || !selectedFixture}
          >
            4-Way
          </button>
        </div>
      </header>

      <section className="workspace">
        <aside className="control-panel">
          <section className="panel-section">
            <h2>Generate</h2>
            <label>
              Fixture
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
              Provider
              <select
                value={state.provider}
                onChange={event =>
                  dispatch({
                    type: 'selectProvider',
                    provider: event.currentTarget.value as LipMaskProvider,
                  })
                }
              >
                <option value="vision">Vision</option>
                <option value="mediapipe">MediaPipe</option>
              </select>
            </label>
            <label>
              Assist
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
                <option value="uvOnly">UV Only</option>
                <option value="blendshapeAssist">Blendshape Assist</option>
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
            <h2>Gate</h2>
            <dl className="gate-list">
              <dt>Status</dt>
              <dd>{lastResult?.status ?? state.status}</dd>
              <dt>UV</dt>
              <dd>{String(Boolean(lastResult?.uvMaskReady))}</dd>
              <dt>Round-trip</dt>
              <dd>{String(Boolean(lastResult?.roundTripReady))}</dd>
              <dt>Runtime</dt>
              <dd>{String(Boolean(lastResult?.runtimeApplyReady))}</dd>
            </dl>
          </section>
        </aside>

        <section className="inspect-panel">
          <PreviewGrid fixture={selectedFixture} result={lastResult} />
          <CompareGrid results={compareResults} />
          <PayloadPanel payload={payloadPreview} />
          <WarningsPanel warnings={warnings} />
        </section>
      </section>
    </main>
  );
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
        <h2>Adjustment</h2>
        <button type="button" onClick={onReset}>
          Reset
        </button>
      </div>
      <div className="range-stack">
        {ADJUSTMENT_FIELDS.map(key => (
          <div className="range-row" key={key}>
            <label htmlFor={`range-${key}`}>
              {key}
              <input
                id={`range-${key}`}
                type="range"
                min="-1"
                max="1"
                step="0.05"
                value={adjustment[key]}
                onChange={event =>
                  onChange(key, Number(event.currentTarget.value))
                }
              />
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
}: {
  fixture?: LipGenerateFixture;
  result?: ServerGenerateResult;
}) {
  return (
    <section className="preview-grid">
      <PreviewFigure title="Frame" src={artifactUrl(fixture?.framePath)} />
      <PreviewFigure title="2D Mask" src={artifactUrl(result?.maskOutputs?.mask)} />
      <PreviewFigure title="UV Texture" src={artifactUrl(result?.package?.uvMaskTexture)} />
      <PreviewFigure
        title="Round-trip"
        src={artifactUrl(result?.package?.roundTripPreview)}
      />
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

function CompareGrid({ results }: { results: ServerGenerateResult[] }) {
  return (
    <section className="compare-section">
      <div className="section-heading">
        <h2>Compare</h2>
        <span>Vision/MediaPipe x UV/Assist</span>
      </div>
      <div className="compare-grid">
        {results.map(result => {
          const score = result.package?.uvCoverageMetadata?.roundTripScore;
          return (
            <article
              className="compare-card"
              key={`${result.provider}-${result.expressionMode}-${result.generatedMaskId}`}
            >
              <header>
                <strong>
                  {result.provider} / {result.expressionMode}
                </strong>
                <small>{result.status}</small>
              </header>
              <img
                src={artifactUrl(result.package?.roundTripPreview)}
                alt={`${result.provider} ${result.expressionMode}`}
              />
              <header>
                <small>
                  IoU {score?.iou ?? '-'} · UV {String(result.uvMaskReady)}
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
    <section className="payload-section">
      <div className="section-heading">
        <h2>Payload</h2>
        <span>RN/Unity handoff preview</span>
      </div>
      <pre>{JSON.stringify(payload, null, 2)}</pre>
    </section>
  );
}

function WarningsPanel({ warnings }: { warnings: string[] }) {
  return (
    <section className="payload-section">
      <div className="section-heading">
        <h2>Warnings</h2>
        <span>ready / partial / blocked evidence</span>
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
