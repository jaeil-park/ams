<template>
  <div class="space-y-6 font-sans">
    <!-- Header -->
    <div class="flex items-center justify-between select-none">
      <div>
        <h1 class="text-xl font-bold text-slate-800">워런티 조회</h1>
        <p class="text-xs text-slate-400 mt-1">Dell·HPE 시리얼을 붙여넣으면 제조사 워런티(보증) 기간을 자동으로 조회합니다</p>
      </div>
      <AppButton variant="secondary" class="text-xs px-3 py-1.5" :loading="reloading" @click="reloadAll">새로고침</AppButton>
    </div>

    <!-- 조회 경로 상태 -->
    <div class="grid grid-cols-1 sm:grid-cols-2 gap-4 select-none">
      <div class="bg-white p-4 rounded-lg border border-slate-200 shadow-sm">
        <span class="block text-4xs font-bold text-slate-400 uppercase tracking-wider">Dell</span>
        <h3 class="text-sm font-bold text-slate-800 mt-1">
          {{ state?.dell_mode === 'API' ? 'TechDirect API 자동 조회' : 'Dell 조회 확장 프로그램 대기' }}
        </h3>
        <p class="text-xs text-slate-500 mt-1">
          <template v-if="state?.dell_mode === 'API'">요청 즉시 Dell 공식 API로 조회합니다.</template>
          <template v-else>
            Dell 건은 '확장 프로그램 대기'로 쌓입니다. Dell 지원 사이트를 연 브라우저에서
            <b>AMS Dell 워런티 조회</b> 확장 프로그램의 [대기 건 처리]를 눌러 주세요.
            <span v-if="openDell"> (현재 대기 {{ openDell }}건)</span>
          </template>
        </p>
      </div>
      <div class="bg-white p-4 rounded-lg border shadow-sm" :class="hpeCardClass">
        <span class="block text-4xs font-bold text-slate-400 uppercase tracking-wider">HPE</span>
        <h3 class="text-sm font-bold mt-1" :class="hpeTitleClass">HPE 포털 자동 조회 — {{ hpeLabel }}</h3>
        <p class="text-xs text-slate-500 mt-1">
          {{ hpe?.message || '작업자(warranty-worker) 응답 기록이 없습니다.' }}
          <span v-if="hpe?.last_seen" class="text-slate-400"> · 마지막 응답 {{ fmtTime(hpe.last_seen) }}</span>
        </p>
      </div>
    </div>

    <!-- 입력 -->
    <div class="bg-white p-4 rounded-lg border border-slate-200 shadow-sm space-y-3">
      <label class="block text-xs font-semibold text-slate-600">
        시리얼 (줄바꿈·쉼표·공백으로 구분, 최대 200건)
      </label>
      <textarea
        v-model="serialText"
        rows="6"
        placeholder="8MN7CC4&#10;SGHD45FLRB&#10;CN703816MW"
        class="block w-full px-3 py-2 border border-slate-300 rounded-md font-mono text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
      />
      <div class="flex flex-wrap items-center gap-4">
        <span class="text-xs text-slate-500">입력 {{ parsedSerials.length }}건</span>
        <label class="flex items-center gap-2 text-xs text-slate-600">
          제조사
          <select v-model="vendor" class="text-xs border border-slate-300 rounded px-2 py-1.5">
            <option value="AUTO">자동 판별</option>
            <option value="DELL">Dell</option>
            <option value="HPE">HPE</option>
          </select>
        </label>
        <label class="flex items-center gap-2 text-xs text-slate-600">
          <input v-model="applyToInventory" type="checkbox" class="rounded border-slate-300" />
          AMS에 등록된 서버는 워런티까지 자동 반영
        </label>
        <div class="flex-1" />
        <AppButton variant="secondary" class="text-xs px-3 py-1.5" :disabled="!rows.length" @click="downloadCsv">
          엑셀(CSV) 다운로드
        </AppButton>
        <AppButton variant="primary" class="text-xs px-4 py-1.5" :loading="submitting" :disabled="!parsedSerials.length" @click="submit">
          조회
        </AppButton>
      </div>
      <p v-if="error" class="text-xs text-rose-600">{{ error }}</p>
    </div>

    <!-- 결과 -->
    <div class="bg-white rounded-lg border border-slate-200 shadow-sm overflow-hidden">
      <div class="px-4 py-3 border-b border-slate-100 flex items-center justify-between select-none">
        <h2 class="text-sm font-bold text-slate-700">
          조회 이력
          <span v-if="rows.length" class="text-slate-400 font-normal">{{ rows.length }}건</span>
        </h2>
        <div class="flex items-center gap-3">
          <span v-if="openCount" class="text-xs text-cyan-700">
            진행 중 {{ openCount }}건<template v-if="etaSeconds"> · 예상 약 {{ fmtEta(etaSeconds) }}</template> · 자동 새로고침
          </span>
          <AppButton
            variant="danger"
            class="text-xs px-3 py-1"
            :disabled="!selected.length"
            :loading="deleting"
            @click="deleteSelected"
          >
            선택 삭제{{ selected.length ? ` (${selected.length})` : '' }}
          </AppButton>
        </div>
      </div>
      <div class="overflow-x-auto">
        <table class="min-w-full divide-y divide-slate-200 text-sm">
          <thead class="bg-slate-50 select-none">
            <tr>
              <th class="pl-4 py-3 w-8">
                <input
                  type="checkbox"
                  class="rounded border-slate-300"
                  :checked="allSelected"
                  :disabled="!rows.length"
                  title="전체 선택"
                  @change="toggleAll"
                />
              </th>
              <th class="px-4 py-3 text-left font-semibold text-slate-500 text-xs">시리얼</th>
              <th class="px-4 py-3 text-left font-semibold text-slate-500 text-xs">제조사</th>
              <th class="px-4 py-3 text-left font-semibold text-slate-500 text-xs">상태</th>
              <th class="px-4 py-3 text-left font-semibold text-slate-500 text-xs">시작일</th>
              <th class="px-4 py-3 text-left font-semibold text-slate-500 text-xs">종료일</th>
              <th class="px-4 py-3 text-left font-semibold text-slate-500 text-xs">In/Out</th>
              <th class="px-4 py-3 text-left font-semibold text-slate-500 text-xs">지원 등급</th>
              <th class="px-4 py-3 text-left font-semibold text-slate-500 text-xs">제품</th>
              <th class="px-4 py-3 text-left font-semibold text-slate-500 text-xs">AMS 반영</th>
              <th class="px-4 py-3 text-left font-semibold text-slate-500 text-xs">비고</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100">
            <tr v-if="!rows.length">
              <td colspan="11" class="px-4 py-12 text-center text-slate-400">조회 이력이 없습니다. 시리얼을 입력하고 [조회]를 누르세요.</td>
            </tr>
            <tr
              v-for="r in rows"
              :key="r.id"
              class="hover:bg-slate-50"
              :class="selected.includes(r.id) ? 'bg-blue-50' : r.batch_id === highlightBatch ? 'bg-amber-50' : ''"
              :title="r.batch_id === highlightBatch ? '방금 요청한 조회' : ''"
            >
              <td class="pl-4 py-2">
                <input v-model="selected" type="checkbox" class="rounded border-slate-300" :value="r.id" />
              </td>
              <td class="px-4 py-2 font-mono text-slate-700">{{ r.serial_tag }}</td>
              <td class="px-4 py-2 text-xs">{{ r.vendor }}</td>
              <td class="px-4 py-2 whitespace-nowrap">
                <span class="px-2 py-0.5 rounded-full text-3xs font-bold whitespace-nowrap" :class="STATUS_CLASS[r.status]">
                  {{ STATUS_LABEL[r.status] }}
                </span>
              </td>
              <td class="px-4 py-2 font-mono text-xs text-slate-600">{{ r.start_date || '-' }}</td>
              <td class="px-4 py-2 font-mono text-xs text-slate-600">{{ r.end_date || '-' }}</td>
              <td class="px-4 py-2">
                <span
                  v-if="warrantyInOut(r.end_date)"
                  class="px-2 py-0.5 rounded text-3xs font-bold"
                  :class="warrantyInOut(r.end_date) === 'IN' ? 'bg-emerald-100 text-emerald-700' : 'bg-rose-100 text-rose-700'"
                >
                  {{ warrantyInOut(r.end_date) === 'IN' ? 'Warranty-In' : 'Warranty-Out' }}
                </span>
              </td>
              <td class="px-4 py-2 text-xs text-slate-600 max-w-xs truncate" :title="r.service_level || ''">{{ r.service_level || '-' }}</td>
              <td class="px-4 py-2 text-xs text-slate-500 max-w-xs truncate" :title="r.product_name || ''">{{ r.product_name || '-' }}</td>
              <td class="px-4 py-2 text-xs">
                <span v-if="r.applied" class="text-emerald-600 font-semibold">반영됨</span>
                <span v-else-if="r.inventory_id" class="text-slate-400">AMS 등록 서버</span>
                <span v-else class="text-slate-300">미등록</span>
              </td>
              <td class="px-4 py-2 text-xs text-slate-500 max-w-sm">
                <span class="block truncate" :title="r.error || ''">{{ r.error || '' }}</span>
                <button
                  v-if="r.status === 'ERROR' || r.status === 'NOT_FOUND'"
                  type="button"
                  class="text-blue-600 hover:underline"
                  @click="retry(r.id)"
                >다시 조회</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import AppButton from '@/components/common/AppButton.vue'
import { useUiStore } from '@/stores/ui'
import {
  useWarrantyLookup,
  fetchLookupState,
  warrantyInOut,
  STATUS_LABEL,
  STATUS_CLASS,
  type WarrantyLookupState,
} from '@/composables/useWarrantyLookup'

const uiStore = useUiStore()
const {
  rows, batchId, submitting, error, openCount, etaSeconds,
  lookupSerials, retry, loadRecent, reload, removeLookups,
} = useWarrantyLookup()

// ─── 선택 삭제 ────────────────────────────────────────────────────────────────
const selected = ref<number[]>([])
const deleting = ref(false)
const reloading = ref(false)
const allSelected = computed(() => rows.value.length > 0 && rows.value.every((r) => selected.value.includes(r.id)))

// 목록이 바뀌면 사라진 행은 선택에서 뺀다
watch(rows, (list) => {
  const ids = new Set(list.map((r) => r.id))
  selected.value = selected.value.filter((id) => ids.has(id))
})

function toggleAll() {
  selected.value = allSelected.value ? [] : rows.value.map((r) => r.id)
}

async function deleteSelected() {
  const ids = [...selected.value]
  const open = rows.value.filter((r) => ids.includes(r.id) && ['PENDING', 'RUNNING', 'WAITING_EXTENSION'].includes(r.status)).length
  const lines = [`선택한 조회 기록 ${ids.length}건을 삭제할까요?`]
  if (open) lines.push(`진행 중인 ${open}건은 조회도 취소됩니다.`)
  lines.push('(이미 서버 워런티에 반영된 값은 그대로 유지됩니다.)')
  const msg = lines.join('\n')
  if (!window.confirm(msg)) return
  deleting.value = true
  try {
    const n = await removeLookups(ids)
    selected.value = []
    uiStore.addToast(`조회 기록 ${n}건을 삭제했습니다.`, 'success')
    loadState()
  } catch {
    uiStore.addToast('삭제에 실패했습니다.', 'error')
  } finally {
    deleting.value = false
  }
}

async function reloadAll() {
  reloading.value = true
  try {
    await Promise.all([loadState(), reload()])
  } catch {
    uiStore.addToast('새로고침에 실패했습니다.', 'error')
  } finally {
    reloading.value = false
  }
}
const LAST_BATCH_KEY = 'ams.warranty.lastBatch'
// 결과 표는 항상 전체 조회 이력(최근 100건)을 보여 주고, 마지막 요청 건만 노란색으로 강조한다
const highlightBatch = ref<string | null>(null)

// 마지막 조회 요청 번호 — 다른 메뉴에 갔다 와도 방금 요청한 건을 강조하기 위한 브라우저 보관값
function saveLastBatch(id: string | null) {
  try {
    if (id) localStorage.setItem(LAST_BATCH_KEY, id)
    else localStorage.removeItem(LAST_BATCH_KEY)
  } catch {
    // 저장소를 쓸 수 없는 환경이면 기억하지 않는다
  }
}

function readLastBatch(): string | null {
  try {
    return localStorage.getItem(LAST_BATCH_KEY)
  } catch {
    return null
  }
}

function fmtEta(sec: number) {
  return sec < 60 ? `${sec}초` : `${Math.ceil(sec / 60)}분`
}

const serialText = ref('')
const vendor = ref<'AUTO' | 'DELL' | 'HPE'>('AUTO')
const applyToInventory = ref(true)
const state = ref<WarrantyLookupState | null>(null)

const parsedSerials = computed(() => {
  const seen = new Set<string>()
  return serialText.value
    .split(/[\s,;]+/)
    .map((s) => s.trim().toUpperCase())
    .filter((s) => s && !seen.has(s) && seen.add(s))
})

const openDell = computed(() => state.value?.open_counts?.DELL ?? 0)
const hpe = computed(() => state.value?.workers?.HPE ?? null)
const HPE_LABEL: Record<string, string> = {
  READY: '정상',
  BUSY: '조회 중',
  LOGIN_REQUIRED: 'HPE 재로그인 필요',
  ERROR: '오류',
  STOPPED: '작업자 중지됨',
}
const hpeLabel = computed(() => (hpe.value ? HPE_LABEL[hpe.value.state] ?? hpe.value.state : '작업자 미실행'))
const hpeOk = computed(() => hpe.value && ['READY', 'BUSY'].includes(hpe.value.state))
const hpeCardClass = computed(() => (hpeOk.value ? 'border-slate-200 bg-white' : 'border-amber-300 bg-amber-50'))
const hpeTitleClass = computed(() => (hpeOk.value ? 'text-slate-800' : 'text-amber-700'))

function fmtTime(iso: string) {
  return new Date(iso).toLocaleString('ko-KR', { hour12: false })
}

async function loadState() {
  try {
    state.value = await fetchLookupState()
  } catch {
    uiStore.addToast('조회 경로 상태를 불러오지 못했습니다.', 'error')
  }
}

async function submit() {
  try {
    await lookupSerials(parsedSerials.value, vendor.value, applyToInventory.value)
    highlightBatch.value = batchId.value
    saveLastBatch(batchId.value)
    uiStore.addToast(`${parsedSerials.value.length}건 조회를 요청했습니다.`, 'success')
    await loadRecent()
    loadState()
  } catch {
    uiStore.addToast(error.value || '조회 요청 실패', 'error')
  }
}

function downloadCsv() {
  const head = ['시리얼', '제조사', '상태', '시작일', '종료일', 'In/Out', '지원 등급', '제품', 'AMS 반영', '비고']
  const lines = rows.value.map((r) => [
    r.serial_tag, r.vendor, STATUS_LABEL[r.status], r.start_date ?? '', r.end_date ?? '',
    warrantyInOut(r.end_date) ?? '', r.service_level ?? '', r.product_name ?? '',
    r.applied ? '반영됨' : '', r.error ?? '',
  ])
  const csv = [head, ...lines]
    .map((cols) => cols.map((c) => `"${String(c).replace(/"/g, '""')}"`).join(','))
    .join('\r\n')
  const blob = new Blob(['﻿' + csv], { type: 'text/csv;charset=utf-8' })
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = `warranty_lookup_${new Date().toISOString().slice(0, 10)}.csv`
  a.click()
  URL.revokeObjectURL(a.href)
}

onMounted(async () => {
  loadState()
  highlightBatch.value = readLastBatch()
  try {
    await loadRecent()
  } catch {
    uiStore.addToast('조회 이력을 불러오지 못했습니다.', 'error')
  }
})
</script>
