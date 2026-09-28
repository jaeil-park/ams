/**
 * 클립보드 복사 유틸
 *
 * AMS는 사내망에서 http 로 접속하므로 보안 컨텍스트(https/localhost)가 아니다.
 * 이 경우 navigator.clipboard 가 아예 없으므로, 구형 execCommand 방식으로 대체한다.
 */
export async function copyText(text: string): Promise<boolean> {
  // 보안 컨텍스트에서는 표준 API를 쓴다
  if (navigator.clipboard && window.isSecureContext) {
    try {
      await navigator.clipboard.writeText(text)
      return true
    } catch {
      // 권한 거부 등 — 아래 대체 방식으로 넘어간다
    }
  }

  try {
    const textarea = document.createElement('textarea')
    textarea.value = text
    // 화면 밖에 두되 focus 가 가능해야 복사가 동작한다
    textarea.style.position = 'fixed'
    textarea.style.top = '-1000px'
    textarea.style.opacity = '0'
    textarea.setAttribute('readonly', '')
    document.body.appendChild(textarea)
    textarea.select()
    textarea.setSelectionRange(0, text.length)
    const ok = document.execCommand('copy')
    document.body.removeChild(textarea)
    return ok
  } catch {
    return false
  }
}
