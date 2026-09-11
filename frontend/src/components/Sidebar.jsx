import { RippleButton } from './ui/ripple-button.jsx'

function Sidebar({ sessions, activeSessionId, onSelectSession, onNewChat, onHideSession }) {
  return (
    <aside className="relative z-10 flex w-72 shrink-0 flex-col border-r border-slate-200/80 bg-white/50 backdrop-blur-sm">
      <div className="p-4">
        <RippleButton
          onClick={onNewChat}
          rippleColor="#dcbd76"
          className="w-full rounded-xl border-brass-500/50 bg-white/80 py-2.5 text-brass-600"
        >
          + New chat
        </RippleButton>
      </div>

      <div className="flex-1 space-y-1 overflow-y-auto px-3 pb-4">
        <p className="px-2 pb-2 pt-1 text-xs font-medium uppercase tracking-wider text-slate-400">
          History
        </p>

        {sessions.length === 0 && (
          <p className="px-2 py-4 text-center text-xs text-slate-400">No conversations yet</p>
        )}

        {sessions.map((session) => {
          const isActive = session.session_id === activeSessionId
          return (
            <div
              key={session.session_id}
              className={`flex items-center gap-2 rounded-lg px-2 py-1.5 transition-colors ${
                isActive
                  ? 'bg-brass-500/15 text-brass-700 ring-1 ring-inset ring-brass-500/30'
                  : 'text-slate-700 hover:bg-white/80'
              }`}
            >
              <button
                onClick={() => onSelectSession(session.session_id)}
                className="block min-w-0 flex-1 truncate px-1 py-2 text-left text-sm"
              >
                {session.title || 'New chat'}
              </button>

              {onHideSession && (
                <button
                  type="button"
                  onClick={(event) => {
                    event.stopPropagation()
                    onHideSession(session.session_id)
                  }}
                  className="rounded-md px-1.5 py-1 text-[11px] font-medium text-slate-400 transition-colors hover:bg-slate-200 hover:text-slate-600"
                  aria-label={`Hide ${session.title || 'chat'} from sidebar`}
                >
                  Hide
                </button>
              )}
            </div>
          )
        })}
      </div>
    </aside>
  )
}

export default Sidebar
