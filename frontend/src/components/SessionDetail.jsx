import { NoiseTexture } from './ui/noise-texture.jsx'

const formatDate = (value) => {
  if (!value) return '—'

  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString()
}

function SessionDetail({ session, onBackToExplorer }) {
  if (!session) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-white px-6">
        <div className="rounded-2xl border border-slate-200 bg-white p-6 text-slate-500">
          Loading session...
        </div>
      </div>
    )
  }

  const turns = session.turns || []

  return (
    <div className="relative flex min-h-screen overflow-hidden bg-white">
      <NoiseTexture
        className="z-0 opacity-70 mix-blend-multiply"
        frequency={0.55}
        octaves={4}
        slope={0.4}
        noiseOpacity={0.85}
      />

      <div className="relative z-10 w-full px-6 py-8">
        <div className="mx-auto max-w-5xl rounded-3xl border border-slate-200 bg-white/80 p-6 shadow-sm backdrop-blur-sm">
          <div className="mb-6 flex items-center justify-between gap-3">
            <div>
              <p className="text-xs font-medium uppercase tracking-[0.2em] text-slate-400">
                Session Detail
              </p>
              <h1 className="mt-2 font-display text-2xl font-semibold text-slate-900">
                {session.session_id}
              </h1>
            </div>

            <button
              onClick={onBackToExplorer}
              className="rounded-full border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-700 transition-colors hover:border-brass-500/60 hover:text-brass-600"
            >
              Back to sessions
            </button>
          </div>

          <div className="mb-6 grid gap-4 rounded-2xl border border-slate-200 bg-slate-50 p-4 md:grid-cols-4">
            <div>
              <div className="text-xs uppercase tracking-wide text-slate-400">Summary</div>
              <div className="mt-1 text-sm text-slate-700">{session.summary || '—'}</div>
            </div>
            <div>
              <div className="text-xs uppercase tracking-wide text-slate-400">Messages</div>
              <div className="mt-1 text-sm text-slate-700">{session.message_count ?? turns.length}</div>
            </div>
            <div>
              <div className="text-xs uppercase tracking-wide text-slate-400">Last updated</div>
              <div className="mt-1 text-sm text-slate-700">{formatDate(session.last_message_at)}</div>
            </div>
            <div>
              <div className="text-xs uppercase tracking-wide text-slate-400">Session ID</div>
              <div className="mt-1 break-all font-mono text-xs text-slate-600">{session.session_id}</div>
            </div>
          </div>

          <div className="space-y-4">
            {turns.length === 0 && (
              <div className="rounded-2xl border border-dashed border-slate-300 bg-white px-4 py-6 text-center text-slate-500">
                No stored turns found for this session.
              </div>
            )}

            {turns.map((turn, index) => (
              <div key={`${turn.created_at ?? index}-${index}`} className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
                <div className="mb-3 flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 pb-2">
                  <div className="text-xs font-medium uppercase tracking-[0.2em] text-slate-400">
                    Turn {index + 1}
                  </div>
                  <div className="text-[11px] text-slate-500">{formatDate(turn.created_at)}</div>
                </div>

                <div className="space-y-4">
                  <div>
                    <div className="mb-1 text-xs font-medium uppercase tracking-[0.15em] text-slate-400">
                      User
                    </div>
                    <div className="whitespace-pre-wrap rounded-xl bg-slate-50 p-3 text-sm text-slate-700">
                      {turn.query}
                    </div>
                  </div>

                  <div>
                    <div className="mb-1 text-xs font-medium uppercase tracking-[0.15em] text-slate-400">
                      Assistant
                    </div>
                    <div className="whitespace-pre-wrap rounded-xl border border-slate-200 bg-white p-3 text-sm text-slate-700">
                      {turn.generation}
                    </div>
                  </div>

                  <div className="grid gap-2 border-t border-slate-100 pt-3 text-xs text-slate-500 md:grid-cols-3">
                    <div>
                      <span className="font-medium text-slate-400">Safety:</span>{' '}
                      {String(turn.is_safe)}
                    </div>
                    <div>
                      <span className="font-medium text-slate-400">Documents:</span>{' '}
                      {(turn.documents || []).length}
                    </div>
                    <div>
                      <span className="font-medium text-slate-400">Created:</span>{' '}
                      {formatDate(turn.created_at)}
                    </div>
                  </div>

                  {(turn.documents || []).length > 0 && (
                    <div className="mt-3">
                      <div className="mb-1 text-xs font-medium uppercase tracking-[0.15em] text-slate-400">
                        Retrieved documents
                      </div>
                      <ul className="space-y-2">
                        {turn.documents.map((doc, docIndex) => (
                          <li
                            key={`${docIndex}-${doc.slice(0, 40)}`}
                            className="rounded-xl border border-slate-200 bg-slate-50 p-3 text-xs text-slate-600"
                          >
                            {doc}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

export default SessionDetail
