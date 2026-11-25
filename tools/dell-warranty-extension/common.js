/* 팝업과 백그라운드 작업자가 함께 쓰는 함수 */

const store = {
  get: (keys) => chrome.storage.local.get(keys),
  set: (obj) => chrome.storage.local.set(obj),
  del: (keys) => chrome.storage.local.remove(keys),
}

/** Dell 사이트 날짜('2월 28, 2026' / 'Feb 28, 2026' / '2026년 2월 28일') → 'YYYY-MM-DD' */
function toIso(text) {
  if (!text) return null
  const pad = (n) => String(n).padStart(2, '0')
  const mk = (y, m, d) => {
    const dt = new Date(Date.UTC(y, m - 1, d))
    return dt.getUTCMonth() === m - 1 ? `${y}-${pad(m)}-${pad(d)}` : null
  }
  let m = text.match(/(\d{4})\s*년\s*(\d{1,2})\s*월\s*(\d{1,2})\s*일/)
  if (m) return mk(+m[1], +m[2], +m[3])
  m = text.match(/(\d{1,2})\s*월\s*(\d{1,2}),\s*(\d{4})/)
  if (m) return mk(+m[3], +m[1], +m[2])
  m = text.match(/(\d{4})-(\d{2})-(\d{2})/)
  if (m) return mk(+m[1], +m[2], +m[3])
  const MON = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']
  m = text.match(/([A-Za-z]{3})[a-z]*\.?\s+(\d{1,2}),\s*(\d{4})/)
  if (m && MON.includes(m[1].toLowerCase())) return mk(+m[3], MON.indexOf(m[1].toLowerCase()) + 1, +m[2])
  return null
}

// ─── AMS API ───────────────────────────────────────────────────────────────────

async function amsBase() {
  const { amsUrl } = await store.get('amsUrl')
  if (!amsUrl) throw new Error('AMS 주소를 입력하고 로그인하세요.')
  return amsUrl.replace(/\/+$/, '')
}

async function amsFetch(path, opts = {}, retry = true) {
  const base = await amsBase()
  const { accessToken, refreshToken } = await store.get(['accessToken', 'refreshToken'])
  const res = await fetch(`${base}/api/v1${path}`, {
    ...opts,
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${accessToken || ''}`, ...(opts.headers || {}) },
  })
  if (res.status === 401 && retry && refreshToken) {
    const r = await fetch(`${base}/api/v1/auth/refresh`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ refresh_token: refreshToken }),
    })
    if (r.ok) {
      const body = await r.json()
      await store.set({ accessToken: body.access_token })
      return amsFetch(path, opts, false)
    }
    throw new Error('AMS 로그인이 만료되었습니다. 다시 로그인하세요.')
  }
  if (!res.ok) {
    let detail = res.statusText
    try { detail = (await res.json()).detail || detail } catch { /* 본문 없음 */ }
    throw new Error(`AMS ${res.status}: ${detail}`)
  }
  return res.json()
}
