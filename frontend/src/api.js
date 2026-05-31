const API_BASE = 'https://gcaiassistant.onrender.com'

export async function processQuery(query) {
  const res = await fetch(`${API_BASE}/process`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query }),
  })
  if (!res.ok) throw new Error('Failed to process query')
  return res.json()
}

export async function sendFollowUp(previous, userReply) {
  const res = await fetch(`${API_BASE}/followup?user_reply=${encodeURIComponent(userReply)}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(previous),
  })
  if (!res.ok) throw new Error('Failed to send follow-up')
  return res.json()
}
