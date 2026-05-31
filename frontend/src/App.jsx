import { useState, useRef, useEffect } from 'react'
import { processQuery, sendFollowUp } from './api.js'
import { Card, CardContent } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import { Send, Loader2, ChevronRight, MessageSquare, CalendarDays, Pencil, Plus, Trash2, Menu } from 'lucide-react'

const STORAGE_KEY = 'gmail-assistant-chats'

const EXAMPLES = [
  'Schedule a 30 minute meeting with Rahul sometime next week',
  'Email the design team that the release is delayed till Friday',
  'Send a follow-up to John about the pending invoice',
  'Create a calendar event with Priya and Meera tomorrow at 4 PM',
  'Draft an email to all engineering managers about the production issue',
]

function loadChats() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? JSON.parse(raw) : []
  } catch {
    return []
  }
}

function saveChats(chats) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(chats))
  } catch {
  }
}

function makeChat() {
  return {
    id: Date.now().toString(),
    title: 'New conversation',
    messages: [],
    createdAt: Date.now(),
    updatedAt: Date.now(),
  }
}

function getChatTitle(chat, text) {
  if (chat.messages.length > 0) {
    return chat.title
  }
  return text.length > 40 ? `${text.slice(0, 40)}...` : text
}

function formatUpdatedAt(timestamp) {
  return new Date(timestamp).toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function replaceChat(chats, activeChatId, nextChat) {
  return chats.map(chat => (chat.id === activeChatId ? nextChat : chat))
}

function JsonBlock({ data }) {
  return (
    <div className="mt-3 rounded-lg bg-neutral-950 p-4 overflow-x-auto">
      <pre className="text-xs leading-relaxed text-neutral-300 font-mono">
        <code>{JSON.stringify(data, null, 2)}</code>
      </pre>
    </div>
  )
}

function ToolIcon({ tool }) {
  const cls = 'w-3.5 h-3.5 text-neutral-500'
  if (tool === 'schedule_meeting') return <CalendarDays className={cls} />
  if (tool === 'send_email') return <Send className={cls} />
  if (tool === 'draft_email') return <Pencil className={cls} />
  return <MessageSquare className={cls} />
}

function FollowUpForm({ onSubmit, disabled }) {
  const [reply, setReply] = useState('')
  return (
    <div className="flex items-center gap-2.5">
      <Input
        className="h-9 bg-neutral-50 border-neutral-200 rounded-lg px-3 text-sm shadow-none focus-visible:ring-1 focus-visible:ring-black placeholder:text-neutral-400"
        placeholder="Type your answer..."
        value={reply}
        onChange={(e) => setReply(e.target.value)}
        onKeyDown={(e) => e.key === 'Enter' && onSubmit(reply)}
      />
      <Button
        size="sm"
        className="h-9 px-4 bg-black hover:bg-neutral-800 text-white rounded-lg text-xs font-medium"
        onClick={() => onSubmit(reply)}
        disabled={disabled || !reply.trim()}
      >
        Reply
      </Button>
    </div>
  )
}

export default function App() {
  const [chats, setChats] = useState([])
  const [activeChatId, setActiveChatId] = useState(null)
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef(null)

  function persistChats(nextChats) {
    setChats(nextChats)
    saveChats(nextChats)
  }

  useEffect(() => {
    const saved = loadChats()
    if (saved.length > 0) {
      setChats(saved)
      setActiveChatId(saved[0].id)
    } else {
      const chat = makeChat()
      setChats([chat])
      setActiveChatId(chat.id)
      saveChats([chat])
    }
  }, [])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [chats, activeChatId, loading])

  function createChat() {
    const chat = makeChat()
    const nextChats = [chat, ...chats]
    setActiveChatId(chat.id)
    setSidebarOpen(false)
    persistChats(nextChats)
  }

  function deleteChat(id) {
    let nextChats = chats.filter(chat => chat.id !== id)
    if (nextChats.length === 0) {
      nextChats = [makeChat()]
    }
    if (activeChatId === id) {
      setActiveChatId(nextChats[0].id)
    }
    persistChats(nextChats)
  }

  async function handleSend(text) {
    if (!text.trim()) return
    const chat = chats.find(item => item.id === activeChatId)
    if (!chat) return

    setLoading(true)
    setQuery('')

    const userMessage = { type: 'user', text }
    const messages = [...chat.messages, userMessage]
    const updatedChat = {
      ...chat,
      messages,
      title: getChatTitle(chat, text),
      updatedAt: Date.now(),
    }
    const nextChats = replaceChat(chats, activeChatId, updatedChat)
    persistChats(nextChats)

    try {
      const result = await processQuery(text)
      const finishedChat = {
        ...updatedChat,
        messages: [...messages, { type: 'assistant', data: result }],
        updatedAt: Date.now(),
      }
      persistChats(replaceChat(nextChats, activeChatId, finishedChat))
    } catch (err) {
      console.error(err)
      const finishedChat = {
        ...updatedChat,
        messages: [...messages, { type: 'error', text: err.message }],
        updatedAt: Date.now(),
      }
      persistChats(replaceChat(nextChats, activeChatId, finishedChat))
    } finally {
      setLoading(false)
    }
  }

  async function handleFollowUp(index, reply) {
    if (!reply.trim()) return
    const chat = chats.find(item => item.id === activeChatId)
    if (!chat) return

    const previous = chat.messages[index].data
    setLoading(true)

    const messages = [...chat.messages, { type: 'user', text: reply }]
    const updatedChat = { ...chat, messages, updatedAt: Date.now() }
    const nextChats = replaceChat(chats, activeChatId, updatedChat)
    persistChats(nextChats)

    try {
      const result = await sendFollowUp(previous, reply)
      const finishedChat = {
        ...updatedChat,
        messages: [...messages, { type: 'assistant', data: result }],
        updatedAt: Date.now(),
      }
      persistChats(replaceChat(nextChats, activeChatId, finishedChat))
    } catch (err) {
      const finishedChat = {
        ...updatedChat,
        messages: [...messages, { type: 'error', text: err.message }],
        updatedAt: Date.now(),
      }
      persistChats(replaceChat(nextChats, activeChatId, finishedChat))
    } finally {
      setLoading(false)
    }
  }

  const activeChat = chats.find(chat => chat.id === activeChatId)
  const activeMessages = activeChat?.messages || []

  return (
    <div className="h-screen flex bg-white">
      {sidebarOpen && (
        <div className="fixed inset-0 z-20 bg-black/20 md:hidden" onClick={() => setSidebarOpen(false)} />
      )}

      <aside
        className={cn(
          'fixed inset-y-0 left-0 z-30 w-64 bg-neutral-50 border-r flex flex-col transition-transform duration-200 ease-in-out md:relative md:translate-x-0',
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        )}
      >
        <div className="p-4 border-b flex items-center justify-between">
          <span className="text-sm font-semibold text-black">Conversations</span>
          <Button size="icon" variant="ghost" className="h-8 w-8" onClick={createChat}>
            <Plus className="w-4 h-4" />
          </Button>
        </div>
        <div className="flex-1 overflow-y-auto">
          {chats.map(chat => (
            <div
              key={chat.id}
              onClick={() => { setActiveChatId(chat.id); setSidebarOpen(false) }}
              className={cn(
                'group flex items-center justify-between px-4 py-3 cursor-pointer border-b border-neutral-100 hover:bg-neutral-100 transition-colors',
                activeChatId === chat.id && 'bg-neutral-100'
              )}
            >
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium text-black truncate">{chat.title}</p>
                <p className="text-xs text-neutral-400 mt-0.5">{formatUpdatedAt(chat.updatedAt)}</p>
              </div>
              <Button
                size="icon" variant="ghost"
                className="h-7 w-7 shrink-0 opacity-0 group-hover:opacity-100 transition-opacity"
                onClick={(e) => { e.stopPropagation(); deleteChat(chat.id) }}
              >
                <Trash2 className="w-3.5 h-3.5 text-neutral-400" />
              </Button>
            </div>
          ))}
        </div>
      </aside>

      <div className="flex-1 flex flex-col min-w-0">
        <header className="shrink-0 border-b px-4 py-3 flex items-center gap-3 bg-white">
          <Button size="icon" variant="ghost" className="md:hidden h-8 w-8" onClick={() => setSidebarOpen(true)}>
            <Menu className="w-4 h-4" />
          </Button>
          <h1 className="text-base font-semibold text-black">AI Assistant</h1>
          <span className="text-xs text-neutral-400 ml-auto hidden sm:inline">Gmail + Calendar</span>
        </header>

        <div className="flex-1 overflow-y-auto">
          <div className="max-w-3xl mx-auto px-4 py-6">
            {activeMessages.length === 0 ? (
              <div className="flex flex-col items-center justify-center min-h-[40vh] text-center space-y-2">
                <h2 className="text-2xl font-semibold text-black tracking-tight">How can I help?</h2>
                <p className="text-sm text-neutral-500 max-w-sm leading-relaxed">
                  Draft emails, send messages, and schedule calendar events using natural language.
                </p>
                <div className="flex gap-2 overflow-x-auto pt-4 max-w-full">
                  {EXAMPLES.map(ex => (
                    <button
                      key={ex}
                      onClick={() => handleSend(ex)}
                      className="shrink-0 inline-flex items-center gap-1.5 px-3.5 py-2 text-xs border border-neutral-200 rounded-full text-neutral-600 bg-white hover:bg-neutral-50 hover:border-neutral-300 transition-colors text-left leading-snug"
                    >
                      <ChevronRight className="w-3 h-3 text-neutral-400 shrink-0" />
                      {ex}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              <div className="space-y-6 pb-4">
                {activeMessages.map((msg, i) => (
                  <div key={i}>
                    {msg.type === 'user' && (
                      <div className="flex justify-end">
                        <div className="max-w-[85%] bg-black text-white px-5 py-3 rounded-2xl rounded-br-sm text-sm leading-relaxed shadow-sm">
                          {msg.text}
                        </div>
                      </div>
                    )}
                    {msg.type === 'error' && (
                      <div className="flex justify-start">
                        <div className="max-w-[85%] bg-red-50 text-red-700 border border-red-200 px-5 py-3 rounded-2xl rounded-bl-sm text-sm">
                          {msg.text}
                        </div>
                      </div>
                    )}
                    {msg.type === 'assistant' && (
                      <div className="flex justify-start">
                        <Card className="max-w-[95%] border-neutral-200 shadow-sm bg-white">
                          <CardContent className="p-5">
                            <div className="flex items-center gap-3 mb-1">
                              <Badge
                                variant="outline"
                                className="bg-neutral-50 text-neutral-700 border-neutral-200 font-medium text-xs capitalize flex items-center gap-1.5 px-2.5 py-0.5"
                              >
                                <ToolIcon tool={msg.data.tool} />
                                {(msg.data.tool || 'assistant').replace(/_/g, ' ')}
                              </Badge>
                              <span className="text-[11px] text-neutral-400 font-medium tabular-nums">
                                {(msg.data.confidence ?? 0).toFixed(2)} confidence
                              </span>
                            </div>
                            <JsonBlock data={msg.data} />
                            {msg.data.follow_up_question && (
                              <div className="mt-5 pt-4 border-t border-neutral-100">
                                <p className="text-sm font-medium text-black mb-3">{msg.data.follow_up_question}</p>
                                <FollowUpForm onSubmit={reply => handleFollowUp(i, reply)} disabled={loading} />
                              </div>
                            )}
                          </CardContent>
                        </Card>
                      </div>
                    )}
                  </div>
                ))}
                {loading && (
                  <div className="flex justify-start">
                    <Card className="border-neutral-200 shadow-sm bg-white">
                      <CardContent className="p-4 flex items-center gap-3 text-sm text-neutral-500">
                        <Loader2 className="w-4 h-4 animate-spin" />
                        Processing your request
                      </CardContent>
                    </Card>
                  </div>
                )}
                <div ref={bottomRef} />
              </div>
            )}
          </div>
        </div>

        <div className="shrink-0 border-t bg-white">
          <div className="max-w-3xl mx-auto px-4 py-4">
            <div className="flex items-center gap-3">
              <Input
                className="h-11 bg-neutral-50 border-neutral-200 rounded-xl px-4 text-sm shadow-none focus-visible:ring-1 focus-visible:ring-black placeholder:text-neutral-400"
                placeholder="Ask me to send an email or schedule a meeting..."
                value={query}
                onChange={e => setQuery(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && handleSend(query)}
              />
              <Button
                size="icon"
                className="h-11 w-11 rounded-xl bg-black hover:bg-neutral-800 text-white shrink-0"
                onClick={() => handleSend(query)}
                disabled={loading || !query.trim()}
              >
                <Send className="w-4 h-4" />
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
