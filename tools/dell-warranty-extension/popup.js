/*
 * AMS Dell 워런티 조회 확장 프로그램 (Manifest V3)
 *
 * - 사용자가 버튼을 누를 때만 동작한다. (자동 반복 조회 없음)
 * - 조회는 사용자가 연 Dell 지원 사이트 탭 안에서 Dell 사이트가 쓰는 요청 그대로 실행한다.
 *   (Dell 사이트 화면에서 서비스 태그를 직접 검색하는 것과 같은 동작)
 * - AMS 비밀번호는 저장하지 않고, 로그인으로 받은 토큰만 chrome.storage.local 에 둔다.
 */

const $ = (id) => document.getElementById(id)
const DELL_HOME = 'https://www.dell.com/support/contractservices/ko-kr/'
const DELAY_MS = 1500
let lastResults = []

// ─── 공통 ──────────────────────────────────────────────────────────────────────

function log(msg, cls = '') {
  const box = $('log')
  if (box.textContent === '준비됨') box.textContent = ''
  const line = document.createElement('div')
  if (cls) line.className = cls
  line.textContent = msg
  box.appendChild(line)
  box.scrollTop = box.scrollHeight
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms))
const store = {
  get: (keys) => chrome.storage.local.get(keys),
  set: (obj) => chrome.storage.local.set(obj),
  del: (keys) => chrome.storage.local.remove(keys),
}

function parseTags(text) {
  const seen = new Set()
  return text.split(/[\s,;]+/).map((s) => s.trim().toUpperCase()).filter((s) => s && !seen.has(s) && seen.add(s))
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

async function login() {
  const url = $('ams-url').value.trim().replace(/\/+$/, '')
  const email = $('ams-email').value.trim()
  const pw = $('ams-pw').value
  if (!url || !email || !pw) return log('AMS 주소, 이메일, 비밀번호를 모두 입력하세요.', 'err')
  // AMS 주소에 대한 접근 권한 요청 (확장 프로그램 설치 시 모든 사이트 권한을 받지 않기 위해)
  const origin = new URL(url).origin + '/*'
  const granted = await chrome.permissions.request({ origins: [origin] })
  if (!granted) return log('AMS 주소 접근 권한이 거부되었습니다.', 'err')

  const form = new URLSearchParams({ username: email, password: pw })
  const res = await fetch(`${url}/api/v1/auth/login`, {
    method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' }, body: form,
  })
  $('ams-pw').value = ''
  if (!res.ok) return log('AMS 로그인 실패 — 이메일/비밀번호를 확인하세요.', 'err')
  const body = await res.json()
  await store.set({ amsUrl: url, amsEmail: email, accessToken: body.access_token, refreshToken: body.refresh_token })
  log('AMS 로그인 완료', 'ok')
  showLoginState()
}

async function logout() {
  await store.del(['accessToken', 'refreshToken'])
  log('로그아웃했습니다.')
  showLoginState()
}

async function showLoginState() {
  const { amsUrl, amsEmail, accessToken } = await store.get(['amsUrl', 'amsEmail', 'accessToken'])
  if (amsUrl) $('ams-url').value = amsUrl
  if (amsEmail) $('ams-email').value = amsEmail
  $('login-state').textContent = accessToken ? `연결됨 (${amsEmail})` : '로그인 필요'
}

// ─── Dell 사이트 조회 ──────────────────────────────────────────────────────────

/** Dell 지원 사이트 탭을 찾거나 새로 연다. */
async function dellTab() {
  const tabs = await chrome.tabs.query({ url: 'https://www.dell.com/support/*' })
  if (tabs.length) return tabs[0].id
  const tab = await chrome.tabs.create({ url: DELL_HOME, active: false })
  await new Promise((resolve) => {
    const fn = (id, info) => {
      if (id === tab.id && info.status === 'complete') {
        chrome.tabs.onUpdated.removeListener(fn)
        resolve()
      }
    }
    chrome.tabs.onUpdated.addListener(fn)
  })
  await sleep(2000)
  return tab.id
}

/** Dell 탭 안에서 실행 — Dell 사이트의 '지원 서비스 상태 확인'과 같은 요청 */
async function lookupInDellPage(tag) {
  try {
    const encRes = await fetch(`/support/components/detectproduct/encvalue/${encodeURIComponent(tag)}?appname=warranty`, { credentials: 'include' })
    if (!encRes.ok) return { ok: false, http: encRes.status }
    const enc = (await encRes.text()).trim()
    const r = await fetch('/support/contractservices/ko-kr/entitlement/contractservicesapi/v1', {
      method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ assetFormat: 'servicetag', assetId: enc, appName: 'home' }),
    })
    if (!r.ok) return { ok: false, http: r.status }
    return { ok: true, data: await r.json() }
  } catch (e) {
    return { ok: false, error: String(e) }
  }
}

async function lookupTag(tabId, tag) {
  const [{ result }] = await chrome.scripting.executeScript({
    target: { tabId }, world: 'MAIN', func: lookupInDellPage, args: [tag],
  })
  if (!result || !result.ok) {
    const why = result?.http ? `Dell 사이트 응답 ${result.http}` : result?.error || '알 수 없는 오류'
    return { status: 'ERROR', error: `${why} — Dell 탭을 새로고침한 뒤 다시 시도하세요.` }
  }
  const d = result.data || {}
  const start = toIso(d.warrantyStartDate)
  const end = toIso(d.warrantyEndDate)
  if (!end) {
    return { status: 'NOT_FOUND', error: d.warrantyResponseErrorMessage || d.supportServicesHeading || '워런티 정보 없음' }
  }
  return {
    status: 'DONE', start_date: start, end_date: end,
    service_level: d.warrantyDisplayName || null,
    detail: { on_support: d.onSupport, raw_start: d.warrantyStartDate, raw_end: d.warrantyEndDate },
  }
}

// ─── 버튼 동작 ─────────────────────────────────────────────────────────────────

async function processPending() {
  $('btn-pending').disabled = true
  try {
    const { data: items } = await amsFetch('/warranty-lookups/pending-dell?limit=50')
    if (!items.length) return log('처리할 Dell 대기 건이 없습니다.', 'ok')
    log(`Dell 대기 ${items.length}건 처리 시작`)
    const tabId = await dellTab()
    let ok = 0
    for (const it of items) {
      const r = await lookupTag(tabId, it.serial_tag)
      try {
        await amsFetch(`/warranty-lookups/${it.id}/result`, { method: 'POST', body: JSON.stringify(r) })
        if (r.status === 'DONE') ok++
        log(`${it.serial_tag}: ${r.status === 'DONE' ? `${r.start_date} ~ ${r.end_date} (${r.service_level || ''})` : r.error}`,
          r.status === 'DONE' ? 'ok' : 'err')
      } catch (e) {
        log(`${it.serial_tag}: AMS 저장 실패 — ${e.message}`, 'err')
      }
      await sleep(DELAY_MS)
    }
    log(`완료: ${ok}/${items.length}건 저장`, 'ok')
  } catch (e) {
    log(e.message, 'err')
  } finally {
    $('btn-pending').disabled = false
  }
}

async function directLookup() {
  const tags = parseTags($('tags').value)
  if (!tags.length) return log('서비스 태그를 입력하세요.', 'err')
  $('btn-direct').disabled = true
  lastResults = []
  try {
    const tabId = await dellTab()
    for (const t of tags) {
      const r = await lookupTag(tabId, t)
      lastResults.push({ tag: t, ...r })
      log(`${t}: ${r.status === 'DONE' ? `${r.start_date} ~ ${r.end_date} (${r.service_level || ''})` : r.error}`,
        r.status === 'DONE' ? 'ok' : 'err')
      await sleep(DELAY_MS)
    }
  } catch (e) {
    log(e.message, 'err')
  } finally {
    $('btn-direct').disabled = false
  }
}

async function copyResults() {
  if (!lastResults.length) return log('복사할 직접 조회 결과가 없습니다.', 'err')
  const lines = [['서비스태그', '상태', '시작일', '종료일', '지원등급', '비고'].join('\t')]
  for (const r of lastResults) {
    lines.push([r.tag, r.status, r.start_date || '', r.end_date || '', r.service_level || '', r.error || ''].join('\t'))
  }
  await navigator.clipboard.writeText(lines.join('\n'))
  log('결과를 복사했습니다. 엑셀에 붙여넣으세요.', 'ok')
}

$('btn-login').addEventListener('click', () => login().catch((e) => log(e.message, 'err')))
$('btn-logout').addEventListener('click', logout)
$('btn-pending').addEventListener('click', processPending)
$('btn-direct').addEventListener('click', directLookup)
$('btn-copy').addEventListener('click', copyResults)
showLoginState()
