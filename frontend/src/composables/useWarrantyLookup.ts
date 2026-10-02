import { ref, computed, onUnmounted } from 'vue'
import api from '@/utils/api'

/**
 * 제조사 워런티 자동 조회 (POST /warranty-lookups → 결과 폴링)
 * - Dell: TechDirect API 키가 있으면 즉시, 없으면 Dell 조회 확장 프로그램이 처리할 때까지 WAITING_EXTENSION
 * - HPE : warranty-worker 컨테이너가 HPE 포털에서 조회 (건당 10~20초)
 */

export type LookupStatus = 'PENDING' | 'RUNNING' | 'WAITING_EXTENSION' | 'DONE' | 'NOT_FOUND' | 'ERROR'

export interface WarrantyLookupRow {
  id: number
  batch_id: string
  serial_tag: string
  vendor: 'DELL' | 'HPE' | 'UNKNOWN'
  status: LookupStatus
  inventory_id: number | null
  apply_to_inventory: boolean
  applied: boolean
  start_date: string | null
  end_date: string | null
  service_level: string | null
  product_name: string | null
  source: string | null
  error: string | null
  created_at: string | null
}

export interface WarrantyLookupState {
  dell_mode: 'API' | 'EXTENSION'
  workers: Record<string, { state: string; message: string | null; last_seen: string }>
  open_counts: Record<string, number>
}

const OPEN: LookupStatus[] = ['PENDING', 'RUNNING', 'WAITING_EXTENSION']

export const STATUS_LABEL: Record<LookupStatus, string> = {
  PENDING: '대기',
  RUNNING: '조회 중',
  WAITING_EXTENSION: '확장 프로그램 대기',
  DONE: '완료',
  NOT_FOUND: '정보 없음',
  ERROR: '오류',
}

export const STATUS_CLASS: Record<LookupStatus, string> = {
  PENDING: 'bg-slate-100 text-slate-600',
  RUNNING: 'bg-cyan-100 text-cyan-700',
  WAITING_EXTENSION: 'bg-amber-100 text-amber-700',
  DONE: 'bg-emerald-100 text-emerald-700',
  NOT_FOUND: 'bg-orange-100 text-orange-700',
  ERROR: 'bg-rose-100 text-rose-700',
}

/** 오늘 기준 워런티 In/Out */
export function warrantyInOut(end: string | null): 'IN' | 'OUT' | null {
  if (!end) return null
  return end >= new Date().toISOString().slice(0, 10) ? 'IN' : 'OUT'
}

export function useWarrantyLookup(pollMs = 3000) {
  const rows = ref<WarrantyLookupRow[]>([])
  const batchId = ref<string | null>(null)
  const submitting = ref(false)
  const error = ref<string | null>(null)
  let timer: ReturnType<typeof setTimeout> | null = null

  const openCount = computed(() => rows.value.filter((r) => OPEN.includes(r.status)).length)
  const isPolling = computed(() => timer !== null)

  function stop() {
    if (timer) clearTimeout(timer)
    timer = null
  }

  async function refresh() {
    if (!batchId.value) return
    const res = await api.get('/warranty-lookups', { params: { batch_id: batchId.value } })
    rows.value = res.data.data
  }

  function schedule() {
    stop()
    if (!openCount.value) return
    timer = setTimeout(async () => {
      timer = null
      try {
        await refresh()
      } catch {
        // 일시적인 네트워크 오류는 다음 주기에 다시 시도
      }
      schedule()
    }, pollMs)
  }

  async function start(path: '' | '/inventory', body: Record<string, unknown>) {
    stop()
    submitting.value = true
    error.value = null
    try {
      const res = await api.post(`/warranty-lookups${path}`, body)
      batchId.value = res.data.data.batch_id
      rows.value = res.data.data.rows
      schedule()
      return rows.value
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } } }
      error.value = err?.response?.data?.detail || '워런티 조회 요청에 실패했습니다.'
      throw e
    } finally {
      submitting.value = false
    }
  }

  /** 시리얼 목록 조회 */
  function lookupSerials(serials: string[], vendor: 'AUTO' | 'DELL' | 'HPE', applyToInventory: boolean) {
    return start('', { serials, vendor, apply_to_inventory: applyToInventory })
  }

  /** AMS 서버(id 목록 또는 프로젝트) 조회 + 서버 워런티 반영 */
  function lookupInventory(opts: { inventoryIds?: number[]; projectId?: number; apply?: boolean }) {
    return start('/inventory', {
      inventory_ids: opts.inventoryIds ?? null,
      project_id: opts.projectId ?? null,
      apply_to_inventory: opts.apply ?? true,
    })
  }

  async function retry(id: number) {
    await api.post(`/warranty-lookups/${id}/retry`)
    if (batchId.value) {
      await refresh()
    } else {
      await loadRecent()
    }
    schedule()
  }

  /** 이전 요청(batch_id) 결과를 다시 불러와 진행 중이면 이어서 새로고침 */
  async function restore(id: string) {
    stop()
    batchId.value = id
    await refresh()
    schedule()
  }

  /** 최근 조회 이력 (요청 구분 없이 최근 limit 건) */
  async function loadRecent(limit = 100) {
    stop()
    batchId.value = null
    const res = await api.get('/warranty-lookups', { params: { limit } })
    rows.value = res.data.data
  }

  /** 남은 예상 시간(초): HPE 건당 약 25초, Dell 확장 프로그램 대기 건은 제외 */
  const etaSeconds = computed(() =>
    rows.value.filter((r) => r.vendor === 'HPE' && (r.status === 'PENDING' || r.status === 'RUNNING')).length * 25,
  )

  onUnmounted(stop)

  return {
    rows, batchId, submitting, error, openCount, isPolling, etaSeconds,
    lookupSerials, lookupInventory, refresh, retry, restore, loadRecent, stop,
  }
}

export async function fetchLookupState(): Promise<WarrantyLookupState> {
  const res = await api.get('/warranty-lookups/status')
  return res.data.data
}
