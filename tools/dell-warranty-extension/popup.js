/*
 * AMS Dell 워런티 조회 — 팝업 화면
 * 조회는 background.js 가 실행한다. 이 창을 닫아도 계속 진행되고, 다시 열면 진행 상황이 보인다.
 * AMS 비밀번호는 저장하지 않고, 로그인으로 받은 토큰만 chrome.storage.local 에 둔다.
 */

const $ = (id) => document.getElementById(id)

function log(text, cls = '') {
  $('notice').className = cls
  $('notice').textContent = text
}

function parseTags(text) {
  const seen = new Set()
  return text.split(/[\s,;]+/).map((s) => s.trim().toUpperCase()).filter((s) => s && !seen.has(s) && seen.add(s))
}

async function login() {
  const url = $('ams-url').value.trim().replace(/\/+$/, '')
  const email = $('ams-email').value.trim()
  const pw = $('ams-pw').value
  if (!url || !email || !pw) return log('AMS 주소, 이메일, 비밀번호를 모두 입력하세요.', 'err')
  // 권한 창이 뜨면 팝업이 닫힐 수 있으므로 주소·이메일을 먼저 저장한다
  await store.set({ amsUrl: url, amsEmail: email })
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

// ─── 진행 상황 ─────────────────────────────────────────────────────────────────

function renderJob(job) {
  const run = !!job?.running
  $('btn-pending').disabled = run
  $('btn-direct').disabled = run
  $('btn-stop').disabled = !run
  if (!job) return
  $('progress').textContent = `${run ? '처리 중' : job.aborted ? '중단됨' : '완료'} ${job.done}/${job.total}건 (성공 ${job.ok})`
  const box = $('log')
  box.replaceChildren(...job.log.map(({ text, cls }) => {
    const line = document.createElement('div')
    if (cls) line.className = cls
    line.textContent = text
    return line
  }))
  box.scrollTop = box.scrollHeight
}

async function start(type, tags) {
  log('')
  const res = await chrome.runtime.sendMessage({ cmd: 'start', type, tags })
  if (!res?.ok) log(res?.error || '시작하지 못했습니다.', 'err')
}

async function directLookup() {
  const tags = parseTags($('tags').value)
  if (!tags.length) return log('서비스 태그를 입력하세요.', 'err')
  await start('direct', tags)
}

async function copyResults() {
  const { job } = await store.get('job')
  const results = job?.type === 'direct' ? job.results : []
  if (!results.length) return log('복사할 직접 조회 결과가 없습니다.', 'err')
  const lines = [['No.', '서비스태그', '상태', '시작일', '종료일', '지원등급', '모델', '비고'].join('\t')]
  results.forEach((r, i) => {
    lines.push([i + 1, r.tag, r.status, r.start_date || '', r.end_date || '', r.service_level || '', r.product_name || '', r.error || ''].join('\t'))
  })
  await navigator.clipboard.writeText(lines.join('\n'))
  log('결과를 복사했습니다. 엑셀에 붙여넣으세요.', 'ok')
}

const guard = (fn) => () => fn().catch((e) => log(e.message, 'err'))
$('btn-login').addEventListener('click', guard(login))
$('btn-logout').addEventListener('click', guard(logout))
$('btn-pending').addEventListener('click', guard(() => start('pending')))
$('btn-stop').addEventListener('click', guard(async () => {
  await chrome.runtime.sendMessage({ cmd: 'stop' })
  log('현재 건을 마치고 중지합니다.')
}))
$('btn-direct').addEventListener('click', guard(directLookup))
$('btn-copy').addEventListener('click', guard(copyResults))
chrome.storage.onChanged.addListener((c) => { if (c.job) renderJob(c.job.newValue) })
showLoginState()
store.get('job').then(({ job }) => renderJob(job))
