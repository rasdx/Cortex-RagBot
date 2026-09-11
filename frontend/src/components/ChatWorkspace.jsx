import { AnimatedGradientText } from './ui/animated-gradient-text.jsx'
import { NoiseTexture } from './ui/noise-texture.jsx'
import { RippleButton } from './ui/ripple-button.jsx'
import Sidebar from './Sidebar.jsx'

function ChatWorkspace({
  sessions,
  activeSessionId,
  connected,
  messages,
  input,
  setInput,
  stage,
  isStreaming,
  ingestStatus,
  onSelectSession,
  onNewChat,
  onHideSession,
  onSendMessage,
  onIngest,
  onOpenSessionExplorer,
}) {
  return (
    <div className="relative flex h-screen overflow-hidden bg-white">
      <NoiseTexture
        className="z-0 opacity-70 mix-blend-multiply"
        frequency={0.55}
        octaves={4}
        slope={0.4}
        noiseOpacity={0.85}
      />

      <Sidebar
        sessions={sessions}
        activeSessionId={activeSessionId}
        onSelectSession={onSelectSession}
        onNewChat={onNewChat}
        onHideSession={onHideSession}
      />

      <div className="relative z-10 flex min-w-0 flex-1 flex-col overflow-hidden">
        <header className="flex items-center gap-4 border-b border-slate-200/80 bg-white/50 px-6 py-4 backdrop-blur-sm">
          <h1 className="font-display text-lg font-semibold tracking-tight text-slate-900">
            <AnimatedGradientText> Cortex</AnimatedGradientText>
          </h1>

          <button
            onClick={onOpenSessionExplorer}
            className="rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-600 transition-colors hover:border-brass-500/60 hover:text-brass-600"
          >
            Chat Sessions
          </button>

          <span
            className={`ml-auto flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-medium ${
              connected
                ? 'border-brass-600/40 bg-brass-500/10 text-brass-600'
                : 'border-slate-300 bg-white/70 text-slate-500'
            }`}
          >
            <span
              className={`h-1.5 w-1.5 rounded-full ${
                connected
                  ? 'bg-brass-500 shadow-[0_0_6px_2px_rgba(201,169,97,0.45)]'
                  : 'bg-slate-400'
              }`}
            />
            {connected ? 'Connected' : 'Disconnected'}
          </span>

          {activeSessionId && (
            <span className="rounded-full bg-white/80 px-3 py-1 font-mono text-xs text-slate-500">
              {activeSessionId.slice(0, 8)}
            </span>
          )}
        </header>

        <div className="flex items-center gap-3 border-b border-slate-200/80 bg-white/40 px-6 py-3">
          <label className="flex cursor-pointer items-center gap-2 rounded-full border border-dashed border-slate-300 px-4 py-1.5 text-xs font-medium text-slate-600 transition-colors hover:border-brass-500/60 hover:text-brass-600">
            Upload documents
            <input type="file" multiple onChange={onIngest} className="hidden" />
          </label>
          {ingestStatus && (
            <span className="animate-fade-up text-xs text-slate-500">{ingestStatus}</span>
          )}
        </div>

        <div className="relative z-10 min-h-0 flex-1 space-y-4 overflow-y-auto px-6 py-6">
          {messages.length === 0 && !stage && (
            <div className="flex h-full flex-col items-center justify-center text-center text-slate-500">
              <p className="font-display text-base text-slate-600">
                Ask something about your documents
              </p>
              <p className="mt-1 text-sm">Upload files above, then start the conversation.</p>
            </div>
          )}

          {messages.map((msg, i) => {
            const isLive = isStreaming && msg.role === 'assistant' && i === messages.length - 1
            if (msg.role === 'notice') {
              return (
                <div key={i} className="flex justify-center">
                  <div className="animate-fade-up rounded-lg border border-dashed border-slate-300 bg-white/70 px-4 py-2 text-xs text-slate-500">
                    {msg.text}
                  </div>
                </div>
              )
            }
            const isUser = msg.role === 'user'
            return (
              <div
                key={i}
                className={`flex animate-fade-up ${isUser ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`relative max-w-[70%] overflow-hidden whitespace-pre-wrap rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                    isUser
                      ? 'rounded-br-sm bg-gradient-to-br from-brass-400 to-brass-600 text-ink-950'
                      : 'rounded-bl-sm border border-slate-200 bg-white/80 text-slate-800'
                  }`}
                >
                  {msg.text}
                  {isLive && <span className="typing-caret" />}
                </div>
              </div>
            )
          })}

          {stage && (
            <div className="flex justify-start">
              <div className="flex items-center gap-2 rounded-2xl rounded-bl-sm border border-slate-200 bg-white/80 px-4 py-3 text-sm">
                <span className="flex gap-1">
                  <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-brass-500 [animation-delay:-0.3s]" />
                  <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-brass-500 [animation-delay:-0.15s]" />
                  <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-brass-500" />
                </span>
                <span className="stage-shimmer font-medium">{stage}</span>
              </div>
            </div>
          )}
        </div>

        <div className="flex items-center gap-3 border-t border-slate-200/80 bg-white/50 px-6 py-4 backdrop-blur-sm">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                e.preventDefault()
                onSendMessage()
              }
            }}
            placeholder="Ask a question..."
            className="flex-1 rounded-lg border border-slate-200 bg-white/80 px-4 py-2.5 text-sm text-slate-800 placeholder:text-slate-400 outline-none transition-colors focus:border-brass-500/60"
          />
          <RippleButton
            onClick={onSendMessage}
            disabled={!connected || !input.trim()}
            rippleColor="#e9d49a"
            className="border-brass-500/50 bg-brass-500 px-5 py-2.5 font-medium text-ink-950 disabled:cursor-not-allowed disabled:opacity-50"
          >
            Send
          </RippleButton>
        </div>
      </div>
    </div>
  )
}

export default ChatWorkspace
