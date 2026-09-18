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

        <div v-if="mismatches.length" class="bg-white border border-amber-300 rounded p-3">
          <p class="font-bold text-amber-700 mb-1.5">등록된 값과 다른 항목</p>
          <ul class="space-y-1.5">
            <li v-for="m in mismatches" :key="m.field" class="flex items-center gap-2 flex-wrap">
              <span class="font-semibold text-slate-600 w-20 shrink-0">{{ m.label }}</span>
              <span class="text-slate-400 line-through">{{ m.current || '(비어 있음)' }}</span>
              <span class="text-slate-400">→</span>
              <span class="font-bold text-slate-800">{{ m.po_value }}</span>
              <button
                type="button"
                class="ml-auto px-2 py-0.5 text-3xs font-bold text-white bg-amber-600 rounded hover:bg-amber-700"
                @click="applyMismatch(m)"
              >
                PO 값으로 반영
              </button>
            </li>
          </ul>
        </div>
        <p v-else class="text-emerald-700 font-semibold">등록된 프로젝트 정보와 PO 문서 내용이 일치합니다.</p>
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
const mismatches = ref<any[]>([])
const uploading = ref(false)
const uploadKind = ref('PO')
const fileInput = ref<HTMLInputElement | null>(null)

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

    if (data.parsed) {
      parsed.value = data.parsed
      mismatches.value = data.mismatches || []
      uiStore.addToast(
        data.mismatches?.length
          ? `PO 내용을 읽었습니다. 등록된 값과 다른 항목이 ${data.mismatches.length}건 있습니다.`
          : 'PO 내용을 읽었습니다. 등록된 정보와 일치합니다.',
        data.mismatches?.length ? 'warning' : 'success',
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

async function loadParsed(attachmentId: number) {
  try {
    const res = await api.get(`/attachments/${attachmentId}/parsed`)
    parsed.value = res.data.data.parsed
    mismatches.value = res.data.data.mismatches || []
  } catch (error: any) {
    console.error(error)
    uiStore.addToast(error.response?.data?.detail || 'PO 내용을 읽지 못했습니다.', 'error')
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

/** PO 문서의 값을 프로젝트 필드에 반영 */
async function applyMismatch(m: any) {
  const fieldMap: Record<string, string> = {
    delivery_date: 'scheduled_date',
    requester_email: 'email',
    ship_to_address: 'location',
  }
  const target = fieldMap[m.field]
  if (!target) {
    uiStore.addToast('PO 번호는 자동 반영할 수 없습니다. 직접 확인해 주세요.', 'warning')
    return
  }
  try {
    await api.patch(`/projects/${props.projectId}`, { [target]: m.po_value })
    uiStore.addToast(`${m.label}을(를) PO 값으로 반영했습니다.`, 'success')
    mismatches.value = mismatches.value.filter(x => x.field !== m.field)
    await fetchProject()
    emit('updated')
  } catch (error: any) {
    console.error(error)
    uiStore.addToast(error.response?.data?.detail || '반영 실패', 'error')
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
