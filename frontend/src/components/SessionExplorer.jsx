import { NoiseTexture } from './ui/noise-texture.jsx'

const formatDate = (value) => {
  if (!value) return '—'

  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString()
}

function SessionExplorer({ sessions, onOpenSession, onBackToChat, onDeleteSession }) {
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
        <div className="mx-auto max-w-6xl rounded-3xl border border-slate-200 bg-white/70 p-6 shadow-sm backdrop-blur-sm">
          <div className="mb-6 flex items-center justify-between gap-3">
            <div>
              <p className="text-xs font-medium uppercase tracking-[0.2em] text-slate-400">
                Session Explorer
              </p>
              <h1 className="mt-2 font-display text-2xl font-semibold text-slate-900">
                Chat Sessions
              </h1>
            </div>

            <button
              onClick={onBackToChat}
              className="rounded-full border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-700 transition-colors hover:border-brass-500/60 hover:text-brass-600"
            >
              Back to chat
            </button>
          </div>

          <div className="overflow-hidden rounded-2xl border border-slate-200">
            <table className="min-w-full divide-y divide-slate-200 text-left text-sm">
              <thead className="bg-slate-50 text-slate-600">
                <tr>
                  <th className="px-4 py-3 font-medium">Session ID</th>
                  <th className="px-4 py-3 font-medium">Summary</th>
                  <th className="px-4 py-3 font-medium">Last updated</th>
                  <th className="px-4 py-3 font-medium">Messages</th>
                  <th className="px-4 py-3 font-medium">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 bg-white">
                {sessions.length === 0 && (
                  <tr>
                    <td colSpan="5" className="px-4 py-8 text-center text-slate-500">
                      No persisted sessions found.
                    </td>
                  </tr>
                )}

                {sessions.map((session) => (
                  <tr key={session.session_id} className="align-top">
                    <td className="max-w-[220px] truncate px-4 py-3 font-mono text-xs text-slate-600">
                      {session.session_id}
                    </td>
                    <td className="px-4 py-3 text-slate-700">{session.title || '—'}</td>
                    <td className="px-4 py-3 text-slate-600">{formatDate(session.last_message_at)}</td>
                    <td className="px-4 py-3 text-slate-600">{session.message_count ?? 0}</td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => onOpenSession(session.session_id)}
                          className="rounded-full border border-brass-500/50 bg-brass-500/10 px-3 py-1.5 text-xs font-medium text-brass-700 transition-colors hover:bg-brass-500/20"
                        >
                          View
                        </button>
                        <button
                          onClick={() => onDeleteSession(session.session_id)}
                          className="rounded-full border border-rose-300 bg-rose-50 px-3 py-1.5 text-xs font-medium text-rose-700 transition-colors hover:bg-rose-100"
                        >
                          Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  )
}

export default SessionExplorer
