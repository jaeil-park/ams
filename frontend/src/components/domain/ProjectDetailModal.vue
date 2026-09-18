<template>
  <AppModal :is-open="isOpen" title="프로젝트 상세" size="lg" @close="emit('close')">
    <div v-if="project" class="space-y-5 text-xs font-sans">
      <!-- 1. 기본 정보 -->
      <div class="bg-slate-50 border border-slate-200 rounded-lg p-4">
        <div class="flex items-start justify-between gap-3 mb-3">
          <div class="min-w-0">
            <span class="font-mono text-sm font-bold text-blue-600">{{ project.po_number }}</span>
            <h3 class="text-sm font-bold text-slate-800 mt-0.5 break-words">{{ project.name }}</h3>
          </div>
          <AppBadge :status="project.status" />
        </div>
        <dl class="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-2">
          <div v-for="row in basicRows" :key="row.label" class="flex gap-2">
            <dt class="text-slate-400 font-semibold w-20 shrink-0">{{ row.label }}</dt>
            <dd class="text-slate-700 font-medium break-words">{{ row.value || '-' }}</dd>
          </div>
        </dl>

        <!-- PO 기준 vs 실제 (PO 문서를 읽은 적이 있을 때만) -->
        <div v-if="hasPoReference" class="mt-3 pt-3 border-t border-slate-200">
          <p class="text-4xs font-bold text-slate-400 uppercase tracking-wider mb-1.5">PO 기준 · 실제 비교</p>
          <table class="w-full">
            <thead>
              <tr class="text-4xs text-slate-400 font-bold">
                <th class="text-left py-0.5 w-20"></th>
                <th class="text-left py-0.5">PO 문서</th>
                <th class="text-left py-0.5">실제</th>
              </tr>
            </thead>
            <tbody class="text-slate-700">
              <tr v-if="project.po_delivery_date">
                <td class="text-slate-400 font-semibold py-0.5">납품일정</td>
                <td class="font-mono py-0.5">{{ project.po_delivery_date }}</td>
                <td class="font-mono py-0.5" :class="dateDiffers ? 'font-bold text-amber-700' : ''">
                  {{ project.scheduled_date || '-' }}
                </td>
              </tr>
              <tr v-if="project.po_amount">
                <td class="text-slate-400 font-semibold py-0.5">금액</td>
                <td class="py-0.5">{{ Number(project.po_amount).toLocaleString() }} {{ project.po_currency }}</td>
                <td class="text-slate-400 py-0.5">-</td>
              </tr>
            </tbody>
          </table>
          <p v-if="project.po_variance_note" class="mt-2 text-slate-600 bg-white border border-slate-200 rounded px-2 py-1.5">
            <span class="font-bold text-slate-500">차이 사유 — </span>{{ project.po_variance_note }}
          </p>
        </div>
      </div>

      <!-- PO 미첨부 경고 -->
      <div
        v-if="project.has_po === false"
        class="flex items-start gap-2 bg-amber-50 border border-amber-200 rounded-lg p-3"
      >
        <svg class="h-4 w-4 text-amber-600 shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
        </svg>
        <div>
          <p class="font-bold text-amber-800">PO 문서가 첨부되지 않았습니다</p>
          <p class="text-amber-700 mt-0.5">PO는 필수 첨부 문서입니다. 첨부하지 않으면 이 프로젝트를 <strong>완료 처리할 수 없습니다.</strong></p>
        </div>
      </div>

      <!-- 2. 첨부파일 -->
      <div>
        <div class="flex items-center justify-between mb-2">
          <h4 class="font-bold text-slate-800 select-none">첨부파일</h4>
          <div class="flex items-center gap-2">
            <select
              v-model="uploadKind"
              class="text-3xs font-semibold bg-white border border-slate-300 rounded px-2 py-1 focus:outline-none"
            >
              <option value="PO">PO</option>
              <option value="QUOTE">견적서</option>
              <option value="INSPECTION">검수확인서</option>
              <option value="HANDOVER">인수인계서</option>
              <option value="OTHER">기타</option>
            </select>
            <input
              ref="fileInput"
              type="file"
              class="hidden"
              @change="handleFileSelected"
            />
            <AppButton
              variant="primary"
              class="text-3xs px-3 py-1.5"
              :loading="uploading"
              @click="fileInput?.click()"
            >
              파일 첨부
            </AppButton>
          </div>
        </div>

        <div v-if="attachments.length === 0" class="text-slate-400 text-center py-5 bg-slate-50 rounded border border-dashed border-slate-200">
          첨부된 파일이 없습니다. PO 문서를 첨부하면 내용을 자동으로 읽어들입니다.
        </div>
        <div v-else class="border border-slate-200 rounded divide-y divide-slate-100">
          <div
            v-for="att in attachments"
            :key="att.id"
            class="flex items-center gap-3 px-3 py-2 hover:bg-slate-50"
          >
            <span class="px-1.5 py-0.5 rounded text-4xs font-bold shrink-0" :class="kindBadge(att.kind)">
              {{ kindLabel(att.kind) }}
            </span>
            <span class="flex-1 truncate text-slate-700 font-medium" :title="att.filename">{{ att.filename }}</span>
            <span class="text-slate-400 shrink-0 tabular-nums">{{ formatSize(att.size) }}</span>
            <span class="text-slate-400 shrink-0">{{ formatDate(att.created_at) }}</span>
            <div class="flex items-center gap-1.5 shrink-0">
              <button
                v-if="isPoDoc(att)"
                type="button"
                class="px-2 py-1 text-3xs font-semibold text-violet-700 border border-violet-200 rounded hover:bg-violet-50"
                @click="loadParsed(att.id)"
              >
                내용 보기
              </button>
              <button
                type="button"
                class="px-2 py-1 text-3xs font-semibold text-blue-600 border border-blue-200 rounded hover:bg-blue-50"
                @click="downloadAttachment(att)"
              >
                다운로드
              </button>
              <button
                type="button"
                class="px-2 py-1 text-3xs font-semibold text-red-600 border border-red-200 rounded hover:bg-red-50"
                @click="removeAttachment(att)"
              >
                삭제
              </button>
            </div>
          </div>
        </div>
        <p class="text-4xs text-slate-400 mt-1.5">
          파일당 최대 10MB. 원본은 항상 다운로드로만 열립니다 (외부 문서를 화면에 직접 실행하지 않기 위함).
        </p>
      </div>

      <!-- 3. PO 문서에서 읽어들인 내용 -->
      <div v-if="parsed" class="border border-violet-200 bg-violet-50 rounded-lg p-4">
        <h4 class="font-bold text-violet-800 mb-2 select-none">PO 문서에서 읽어들인 내용</h4>
        <dl class="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-1.5 mb-3">
          <div v-for="row in parsedRows" :key="row.label" class="flex gap-2">
            <dt class="text-violet-400 font-semibold w-24 shrink-0">{{ row.label }}</dt>
            <dd class="text-slate-700 font-medium break-words">{{ row.value }}</dd>
          </div>
        </dl>

        <!-- 경고 -->
        <div v-if="warnings.length" class="bg-red-50 border border-red-200 rounded p-3 mb-3">
          <p v-for="(w, i) in warnings" :key="i" class="text-red-700 font-semibold">{{ w }}</p>
        </div>

        <!-- 자동 반영된 필수 항목 -->
        <div v-if="autoApplied.length" class="bg-white border border-emerald-200 rounded p-3 mb-3">
          <p class="font-bold text-emerald-700 mb-0.5">자동 반영됨 (PO 문서가 원본인 항목)</p>
          <p class="text-4xs text-slate-400 mb-2">
            PO 번호와 PO 기준 금액·요구 납기는 문서가 원본이므로 자동으로 맞췄습니다.
          </p>
          <ul class="space-y-1">
            <li v-for="a in autoApplied" :key="a.field" class="flex items-center gap-2 flex-wrap">
              <span class="font-semibold text-slate-600 w-24 shrink-0">{{ a.label }}</span>
              <span class="text-slate-400 line-through">{{ a.before ?? '(비어 있음)' }}</span>
              <span class="text-slate-400">→</span>
              <span class="font-bold text-emerald-700">{{ a.after }}</span>
            </li>
          </ul>
        </div>

        <!-- 선택 반영 항목 -->
        <div v-if="optional.length" class="bg-white border border-slate-200 rounded p-3">
          <p class="font-bold text-slate-700 mb-0.5">선택 반영 (실제 진행값)</p>
          <p class="text-4xs text-slate-400 mb-2">
            실제 납품이 PO와 다르게 진행되는 경우가 있어 자동으로 덮어쓰지 않습니다.
            PO 값으로 맞출 항목만 체크한 뒤 반영하세요.
          </p>
          <ul class="space-y-1.5">
            <li v-for="o in optional" :key="o.field" class="flex items-start gap-2">
              <input
                :id="`opt-${o.field}`"
                v-model="selectedOptional"
                type="checkbox"
                :value="o.field"
                class="mt-0.5 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
              />
              <label :for="`opt-${o.field}`" class="flex-1 cursor-pointer">
                <div class="flex items-center gap-2 flex-wrap">
                  <span class="font-semibold text-slate-600 w-24 shrink-0">{{ o.label }}</span>
                  <span class="text-slate-400 break-all">{{ o.current || '(비어 있음)' }}</span>
                  <span class="text-slate-400">→</span>
                  <span class="font-bold text-slate-800 break-all">{{ o.po_value }}</span>
                </div>
                <div v-if="o.hint" class="text-4xs text-slate-400 mt-0.5">{{ o.hint }}</div>
              </label>
            </li>
          </ul>
          <div class="flex items-center gap-2 mt-3">
            <AppButton
              variant="primary"
              class="text-3xs px-3 py-1.5"
              :loading="applyingOptional"
              :disabled="selectedOptional.length === 0"
              @click="applySelectedOptional"
            >
              선택 항목 반영 ({{ selectedOptional.length }})
            </AppButton>
            <button
              type="button"
              class="text-3xs font-semibold text-slate-400 hover:text-slate-600"
              @click="selectedOptional = optional.map(o => o.field)"
            >
              전체 선택
            </button>
          </div>
        </div>
        <p v-else-if="!autoApplied.length" class="text-emerald-700 font-semibold">
          PO 문서 내용과 등록된 실제값이 모두 일치합니다.
        </p>

        <!-- 차이 사유 -->
        <div class="mt-3">
          <label class="block font-semibold text-violet-700 mb-1">PO와 다르게 진행된 사유 (선택)</label>
          <div class="flex gap-2">
            <input
              v-model="varianceNote"
              type="text"
              maxlength="500"
              placeholder="예: PO는 2대이나 고객사 요청으로 1대만 선납품, 잔여 1대 10월 예정"
              class="flex-1 px-3 py-2 border border-slate-300 rounded focus:outline-none focus:ring-1 focus:ring-violet-500"
            />
            <AppButton
              variant="secondary"
              class="text-3xs px-3 py-1.5 shrink-0"
              :loading="savingNote"
              @click="saveVarianceNote"
            >
              사유 저장
            </AppButton>
          </div>
        </div>
      </div>

      <!-- 4. 소속 서버/파트 -->
      <div>
        <h4 class="font-bold text-slate-800 mb-2 select-none">이 프로젝트의 서버 / 파트</h4>
        <ProjectItemsPanel :project-id="projectId" />
      </div>
    </div>

    <div v-else class="py-10 text-center text-slate-400 text-xs">프로젝트 정보를 불러오는 중입니다...</div>
  </AppModal>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import api from '@/utils/api'
import { useUiStore } from '@/stores/ui'
import AppBadge from '@/components/common/AppBadge.vue'
import AppButton from '@/components/common/AppButton.vue'
import AppModal from '@/components/common/AppModal.vue'
import ProjectItemsPanel from '@/components/domain/ProjectItemsPanel.vue'

interface Props {
  isOpen: boolean
  projectId: number
  customerName?: string
}

const props = defineProps<Props>()
const emit = defineEmits<{
  (e: 'close'): void
  (e: 'updated'): void
}>()

const uiStore = useUiStore()

const project = ref<any>(null)
const attachments = ref<any[]>([])
const parsed = ref<Record<string, any> | null>(null)
const autoApplied = ref<any[]>([])
const optional = ref<any[]>([])
const warnings = ref<string[]>([])
const selectedOptional = ref<string[]>([])
const applyingOptional = ref(false)
const uploading = ref(false)
const uploadKind = ref('PO')
const fileInput = ref<HTMLInputElement | null>(null)
const varianceNote = ref('')
const savingNote = ref(false)

const hasPoReference = computed(
  () => !!(project.value?.po_delivery_date || project.value?.po_amount),
)

const dateDiffers = computed(() => {
  const p = project.value
  if (!p?.po_delivery_date || !p?.scheduled_date) return false
  return p.po_delivery_date !== p.scheduled_date
})

const PARSED_LABELS: Record<string, string> = {
  po_number: 'PO 번호',
  pr_number: 'PR 번호',
  buyer_name: '발주처',
  requester: '요청자',
  requester_email: '요청자 메일',
  total_amount: '금액',
  delivery_date: '요구 납기',
  ship_to_name: '납품처',
  ship_to_address: '납품 주소',
  item_description: '품목',
}

const basicRows = computed(() => {
  const p = project.value
  if (!p) return []
  return [
    { label: '고객사', value: props.customerName },
    { label: '담당자', value: p.manager },
    { label: '연락처', value: p.phone },
    { label: '이메일', value: p.email },
    { label: '납품일정', value: p.scheduled_date },
    { label: '납품 위치', value: p.location },
  ]
})

const parsedRows = computed(() => {
  if (!parsed.value) return []
  return Object.entries(PARSED_LABELS)
    .filter(([key]) => parsed.value?.[key] !== undefined && parsed.value?.[key] !== null)
    .map(([key, label]) => ({
      label,
      value: key === 'total_amount'
        ? `${Number(parsed.value![key]).toLocaleString()} ${parsed.value!.currency || ''}`.trim()
        : String(parsed.value![key]),
    }))
})

onMounted(() => {
  fetchProject()
  fetchAttachments()
})

async function fetchProject() {
  try {
    const res = await api.get(`/projects/${props.projectId}`)
    project.value = res.data.data
    varianceNote.value = project.value.po_variance_note || ''
  } catch (error) {
    console.error('프로젝트 조회 실패:', error)
    uiStore.addToast('프로젝트 정보를 불러오지 못했습니다.', 'error')
  }
}

async function fetchAttachments() {
  try {
    const res = await api.get(`/projects/${props.projectId}/attachments`)
    attachments.value = res.data.data || []
  } catch (error) {
    console.error('첨부파일 조회 실패:', error)
  }
}

async function handleFileSelected(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return

  const form = new FormData()
  form.append('file', file)
  form.append('kind', uploadKind.value)

  uploading.value = true
  try {
    const res = await api.post(`/projects/${props.projectId}/attachments`, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    const data = res.data.data
    await fetchAttachments()
    // PO 기준값·첨부 여부가 바뀌었을 수 있으므로 프로젝트 정보를 다시 읽는다
    await fetchProject()
    emit('updated')

    if (data.parsed) {
      applyMergeResult(data)
      const autoCount = data.auto_applied?.length || 0
      const optCount = data.optional?.length || 0
      uiStore.addToast(
        autoCount
          ? `PO 내용을 읽어 ${autoCount}개 항목을 자동 반영했습니다.` +
            (optCount ? ` 선택 반영 가능한 항목이 ${optCount}건 있습니다.` : '')
          : optCount
            ? `PO 내용을 읽었습니다. 선택 반영 가능한 항목이 ${optCount}건 있습니다.`
            : 'PO 내용을 읽었습니다. 등록된 정보와 일치합니다.',
        'success',
      )
    } else {
      uiStore.addToast('첨부파일이 등록되었습니다.', 'success')
    }
  } catch (error: any) {
    console.error(error)
    uiStore.addToast(error.response?.data?.detail || '첨부파일 업로드 실패', 'error')
  } finally {
    uploading.value = false
    // 같은 파일을 다시 선택해도 change 이벤트가 뜨도록 초기화
    input.value = ''
  }
}

function applyMergeResult(data: any) {
  parsed.value = data.parsed
  autoApplied.value = data.auto_applied || []
  optional.value = data.optional || []
  warnings.value = data.warnings || []
  selectedOptional.value = []
}

async function loadParsed(attachmentId: number) {
  try {
    const res = await api.get(`/attachments/${attachmentId}/parsed`)
    applyMergeResult(res.data.data)
  } catch (error: any) {
    console.error(error)
    uiStore.addToast(error.response?.data?.detail || 'PO 내용을 읽지 못했습니다.', 'error')
  }
}

/** 체크한 선택 항목만 실제값에 반영한다 */
async function applySelectedOptional() {
  const payload: Record<string, any> = {}
  for (const o of optional.value) {
    if (selectedOptional.value.includes(o.field)) payload[o.field] = o.po_value
  }
  if (Object.keys(payload).length === 0) return

  applyingOptional.value = true
  try {
    await api.patch(`/projects/${props.projectId}`, payload)
    uiStore.addToast(`${Object.keys(payload).length}개 항목을 PO 값으로 반영했습니다.`, 'success')
    optional.value = optional.value.filter(o => !selectedOptional.value.includes(o.field))
    selectedOptional.value = []
    await fetchProject()
    emit('updated')
  } catch (error: any) {
    console.error(error)
    uiStore.addToast(error.response?.data?.detail || '반영 실패', 'error')
  } finally {
    applyingOptional.value = false
  }
}

async function downloadAttachment(att: any) {
  try {
    const res = await api.get(`/attachments/${att.id}/download`, { responseType: 'blob' })
    const url = URL.createObjectURL(res.data)
    const link = document.createElement('a')
    link.href = url
    link.download = att.filename
    link.click()
    URL.revokeObjectURL(url)
  } catch (error) {
    console.error(error)
    uiStore.addToast('다운로드 실패', 'error')
  }
}

async function removeAttachment(att: any) {
  if (!confirm(`'${att.filename}' 첨부파일을 삭제하시겠습니까?`)) return
  try {
    await api.delete(`/attachments/${att.id}`)
    uiStore.addToast('첨부파일이 삭제되었습니다.', 'success')
    await fetchAttachments()
  } catch (error) {
    console.error(error)
    uiStore.addToast('첨부파일 삭제 실패', 'error')
  }
}

async function saveVarianceNote() {
  savingNote.value = true
  try {
    await api.patch(`/projects/${props.projectId}`, { po_variance_note: varianceNote.value || null })
    uiStore.addToast('차이 사유를 저장했습니다.', 'success')
    await fetchProject()
    emit('updated')
  } catch (error: any) {
    console.error(error)
    uiStore.addToast(error.response?.data?.detail || '사유 저장 실패', 'error')
  } finally {
    savingNote.value = false
  }
}

function isPoDoc(att: any) {
  return att.kind === 'PO' && /\.html?$/i.test(att.filename)
}

const KIND_LABELS: Record<string, string> = {
  PO: 'PO',
  QUOTE: '견적서',
  INSPECTION: '검수확인서',
  HANDOVER: '인수인계서',
  OTHER: '기타',
}

const KIND_BADGES: Record<string, string> = {
  PO: 'bg-blue-100 text-blue-700',
  QUOTE: 'bg-emerald-100 text-emerald-700',
  INSPECTION: 'bg-violet-100 text-violet-700',
  HANDOVER: 'bg-amber-100 text-amber-700',
  OTHER: 'bg-slate-100 text-slate-600',
}

function kindLabel(kind: string) {
  return KIND_LABELS[kind] || kind
}

function kindBadge(kind: string) {
  return KIND_BADGES[kind] || KIND_BADGES.OTHER
}

function formatSize(bytes: number) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

function formatDate(d: string) {
  if (!d) return '-'
  return new Date(d).toLocaleDateString('ko-KR', { year: '2-digit', month: '2-digit', day: '2-digit' })
}
</script>
