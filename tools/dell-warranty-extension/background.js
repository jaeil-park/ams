/*
 * AMS Dell 워런티 조회 — 백그라운드 작업자 (Manifest V3 service worker)
 *
 * 팝업 창은 다른 곳을 클릭하면 닫히므로, 조회는 여기서 실행하고 팝업은 진행 상황만 보여 준다.
 * - 사용자가 버튼을 누를 때만 시작한다. (자동 반복 조회 없음)
 * - 진행 상황(job)은 chrome.storage.local 에 두어, 브라우저가 작업자를 재시작해도 이어서 처리한다.
 * - 조회는 Dell 지원 사이트 탭 안에서 Dell 사이트가 쓰는 요청 그대로 실행한다.
 */
importScripts('common.js')

const DELL_HOME = 'https://www.dell.com/support/contractservices/ko-kr/'
const DELAY_MS = 1500
const PAGE_SIZE = 100
const MAX_CONSECUTIVE_ERRORS = 3
const LOG_MAX = 300
const ALARM = 'resume-job'

const sleep = (ms) => new Promise((r) => setTimeout(r, ms))
let running = false
let stopRequested = false

// ─── 작업 상태 ─────────────────────────────────────────────────────────────────

async function saveJob(job) {
  await store.set({ job })
  const left = Math.max(0, job.total - job.done)
  await chrome.action.setBadgeBackgroundColor({ color: job.running ? '#2563eb' : '#be123c' })
  await chrome.action.setBadgeText({ text: job.running ? String(left) : job.aborted ? '!' : '' })
}

function addLog(job, text, cls = '') {
  job.log.push({ text, cls })
  if (job.log.length > LOG_MAX) job.log.splice(0, job.log.length - LOG_MAX)
}

// ─── Dell 사이트 조회 ──────────────────────────────────────────────────────────

/** Dell 지원 사이트 탭을 찾거나 새로 연다. */
async function dellTab() {
  const tabs = await chrome.tabs.query({ url: 'https://www.dell.com/support/*' })
  const ready = tabs.find((t) => !t.discarded)
  if (ready) return ready.id
  const tab = await chrome.tabs.create({ url: DELL_HOME, active: false })
  for (let i = 0; i < 60; i++) {
    await sleep(500)
    if ((await chrome.tabs.get(tab.id)).status === 'complete') break
  }
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
    const data = await r.json()
    // 모델명: 응답의 제품 지원 페이지(ipsOverviewUrl) 제목에서 가져온다. 실패해도 워런티 결과는 그대로 쓴다.
    let title = null
    if (data && data.ipsOverviewUrl) {
      try {
        const page = await fetch(data.ipsOverviewUrl, { credentials: 'include' })
        if (page.ok) {
          const m = (await page.text()).match(/<title[^>]*>([^<]+)<\/title>/i)
          title = m ? m[1].trim() : null
        }
      } catch {
        title = null
      }
    }
    return { ok: true, data, title }
  } catch (e) {
    return { ok: false, error: String(e) }
  }
}

/** 'PowerEdge R760xs Rack Server에 대한 지원 | 개요 | Dell 대한민국' / 'Support for PowerEdge R760 | Overview | Dell US' → 모델명 */
function productFromTitle(title) {
  if (!title) return null
  let s = title.split('|')[0].trim()
  s = s.replace(/에 대한 지원$/, '').replace(/^Support for\s+/i, '').trim()
  return s || null
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
  const product = productFromTitle(result.title)
  if (!end) {
    return {
      status: 'NOT_FOUND', product_name: product,
      error: d.warrantyResponseErrorMessage || d.supportServicesHeading || '워런티 정보 없음',
    }
  }
  return {
    status: 'DONE', start_date: start, end_date: end,
    service_level: d.warrantyDisplayName || null,
    product_name: product,
    detail: { on_support: d.onSupport, raw_start: d.warrantyStartDate, raw_end: d.warrantyEndDate },
  }
}

/** 처리 도중 Dell 탭이 닫혔으면 탭을 다시 열어 한 번 더 시도한다. */
async function lookupWithTab(tag) {
  for (let attempt = 0; ; attempt++) {
    try {
      return await lookupTag(await dellTab(), tag)
    } catch (e) {
      if (attempt >= 1) return { status: 'ERROR', error: `Dell 탭에서 조회하지 못했습니다 — ${e.message}` }
      await sleep(2000)
    }
  }
}

// ─── 작업 실행 ─────────────────────────────────────────────────────────────────

/** 대기열이 비면 다음 대기 건을 가져온다. 이미 시도한 건은 제외한다. (저장 실패 시 무한 반복 방지) */
async function refill(job) {
  if (job.type !== 'pending') return
  const { data } = await amsFetch(`/warranty-lookups/pending-dell?limit=${PAGE_SIZE}`)
  const tried = new Set(job.tried)
  job.queue = data.filter((it) => !tried.has(it.id)).map((it) => ({ id: it.id, tag: it.serial_tag }))
  job.total = Math.max(job.total, job.done + job.queue.length)
}

async function runJob() {
  if (running) return
  running = true
  stopRequested = false
  const { job } = await store.get('job')
  if (!job?.running) {
    running = false
    return
  }
  let errorsInRow = 0
  try {
    for (;;) {
      if (stopRequested) {
        job.aborted = true
        addLog(job, `중지했습니다. (${job.done}/${job.total}건 처리)`, 'err')
        break
      }
      if (!job.queue.length) await refill(job)
      if (!job.queue.length) {
        addLog(job, `완료: ${job.ok}/${job.done}건 조회 성공`, 'ok')
        job.total = job.done
        break
      }
      const it = job.queue[0]
      const r = await lookupWithTab(it.tag)
      let saved = true
      if (job.type === 'pending') {
        try {
          await amsFetch(`/warranty-lookups/${it.id}/result`, { method: 'POST', body: JSON.stringify(r) })
        } catch (e) {
          saved = false
          addLog(job, `${it.tag}: AMS 저장 실패 — ${e.message}`, 'err')
        }
        job.tried.push(it.id)
      } else {
        job.results.push({ tag: it.tag, ...r })
      }
      job.queue.shift()
      job.done++
      const ok = saved && r.status === 'DONE'
      if (ok) job.ok++
      if (saved) {
        addLog(job, `${job.done}. ${it.tag}: ${r.status === 'DONE' ? `${r.start_date} ~ ${r.end_date} (${r.service_level || ''}) ${r.product_name || ''}` : r.error}`,
          ok ? 'ok' : 'err')
      }
      errorsInRow = !saved || r.status === 'ERROR' ? errorsInRow + 1 : 0
      if (errorsInRow >= MAX_CONSECUTIVE_ERRORS) {
        job.aborted = true
        addLog(job, `연속 ${errorsInRow}건 실패로 멈췄습니다. Dell 탭과 AMS 연결을 확인한 뒤 다시 시작하세요.`, 'err')
        break
      }
      await saveJob(job)
      await sleep(DELAY_MS)
    }
  } catch (e) {
    job.aborted = true
    addLog(job, e.message, 'err')
  } finally {
    job.running = false
    running = false
    await chrome.alarms.clear(ALARM)
    await saveJob(job)
  }
}

async function startJob(type, tags) {
  const { job: prev } = await store.get('job')
  if (running || prev?.running) throw new Error('이미 처리 중입니다.')
  const job = { type, running: true, aborted: false, queue: [], tried: [], results: [], log: [], total: 0, done: 0, ok: 0 }
  if (type === 'pending') {
    const { data } = await amsFetch('/warranty-lookups/status')
    job.total = data.open_counts?.DELL ?? 0
    if (!job.total) throw new Error('처리할 Dell 대기 건이 없습니다.')
    addLog(job, `Dell 대기 ${job.total}건 처리 시작`)
  } else {
    job.queue = tags.map((tag) => ({ tag }))
    job.total = tags.length
    addLog(job, `직접 조회 ${job.total}건 시작`)
  }
  await saveJob(job)
  await chrome.alarms.create(ALARM, { periodInMinutes: 1 })
  runJob()
}

chrome.runtime.onMessage.addListener((msg, sender, reply) => {
  if (sender.id !== chrome.runtime.id) return
  if (msg.cmd === 'start') {
    startJob(msg.type, msg.tags).then(() => reply({ ok: true }), (e) => reply({ ok: false, error: e.message }))
    return true
  }
  if (msg.cmd === 'stop') {
    // 작업자가 막 재시작돼 멈춰 있는 상태라면 먼저 작업을 이어받은 뒤 중지 처리한다
    if (!running) runJob()
    stopRequested = true
    reply({ ok: true })
  }
})

// 브라우저가 작업자를 종료했다가 다시 깨우면 이어서 처리한다
chrome.alarms.onAlarm.addListener((a) => { if (a.name === ALARM) runJob() })

// 브라우저를 껐다 켜거나 확장을 새로고침한 경우에는 자동으로 이어 가지 않는다 (다시 눌러야 시작)
async function markInterrupted() {
  await chrome.alarms.clear(ALARM)
  const { job } = await store.get('job')
  if (job?.running && !running) {
    job.running = false
    job.aborted = true
    addLog(job, '브라우저 또는 확장 프로그램이 다시 시작되어 중단되었습니다. 다시 시작하세요.', 'err')
    await saveJob(job)
  }
}
chrome.runtime.onStartup.addListener(markInterrupted)
chrome.runtime.onInstalled.addListener(markInterrupted)
