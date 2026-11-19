<template>
  <AppModal :is-open="isOpen" title="프로젝트 완료 처리" size="md" @close="emit('close')">
    <div class="space-y-5 text-xs font-sans">
      <div>
        <span class="font-mono text-sm font-bold text-blue-600">{{ project?.po_number }}</span>
        <h3 class="text-sm font-bold text-slate-800 mt-0.5 break-words">{{ project?.name }}</h3>
      </div>

      <div v-if="loading" class="py-10 text-center text-slate-400">체크리스트를 확인하는 중입니다...</div>

      <template v-else>
        <!-- 자동 검사 -->
        <div>
          <h4 class="font-bold text-slate-800 mb-1 select-none">자동 확인 항목</h4>
          <p class="text-4xs text-slate-400 mb-2">AMS가 데이터로 직접 확인합니다. 통과해야 완료 처리할 수 있습니다.</p>
          <ul class="border border-slate-200 rounded divide-y divide-slate-100">
            <li
              v-for="c in autoChecks"
              :key="c.key"
              class="px-3 py-2"
              :class="checkState(c) === 'fail' ? 'bg-red-50' : checkState(c) === 'exempt' ? 'bg-amber-50' : 'bg-white'"
            >
              <div class="flex items-center gap-2">
                <svg v-if="checkState(c) === 'pass'" class="h-4 w-4 text-emerald-600 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 13l4 4L19 7" />
                </svg>
                <svg v-else-if="checkState(c) === 'exempt'" class="h-4 w-4 text-amber-600 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M20 12H4" />
                </svg>
                <svg v-else class="h-4 w-4 text-red-500 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M6 18L18 6M6 6l12 12" />
                </svg>
                <span
                  class="font-semibold"
                  :class="checkState(c) === 'fail' ? 'text-red-700' : checkState(c) === 'exempt' ? 'text-amber-800' : 'text-slate-700'"
                >{{ c.label }}</span>
                <span class="ml-auto text-slate-400 text-right">
                  {{ checkState(c) === 'exempt' ? '해당 없음' : c.detail }}
                </span>
              </div>

              <!-- 미충족 + 예외 가능 항목: 해당 없음 처리 -->
              <div v-if="!c.passed && c.exemptable" class="mt-2 pl-6">
                <label class="inline-flex items-center gap-1.5 cursor-pointer text-slate-600">
                  <input
                    v-model="exemptOn[c.key]"
                    type="checkbox"
                    class="rounded border-slate-300 text-amber-600 focus:ring-amber-500"
                  />
                  <span class="font-semibold">이 프로젝트는 해당 없음</span>
                </label>
                <div v-if="exemptOn[c.key]" class="mt-1.5">
                  <input
                    v-model="exemptReason[c.key]"
                    type="text"
                    maxlength="500"
                    :placeholder="EXEMPT_PLACEHOLDER[c.key] || '해당 없는 사유를 입력하세요'"
                    class="w-full px-2.5 py-1.5 border rounded focus:outline-none focus:ring-1"
                    :class="reasonValid(c.key) ? 'border-slate-300 focus:ring-amber-500' : 'border-red-300 focus:ring-red-400'"
                  />
                  <p v-if="!reasonValid(c.key)" class="text-4xs text-red-500 mt-0.5">
                    사유를 {{ MIN_REASON }}자 이상 입력해 주세요. 처리자·시각과 함께 기록됩니다.
                  </p>
                </div>
              </div>
              <p v-else-if="!c.passed && !c.exemptable" class="mt-1 pl-6 text-4xs text-red-500">
                이 항목은 해당 없음 처리가 불가합니다. 실제로 처리한 뒤 완료해 주세요.
              </p>
            </li>
          </ul>
        </div>

        <!-- 수기 확인 -->
        <div>
          <h4 class="font-bold text-slate-800 mb-1 select-none">담당자 확인 항목</h4>
          <p class="text-4xs text-slate-400 mb-2">현장 사실은 AMS가 알 수 없습니다. 직접 확인 후 체크해 주세요.</p>
          <ul class="border border-slate-200 rounded divide-y divide-slate-100">
            <li v-for="m in manualItems" :key="m.key" class="px-3 py-2">
              <label class="flex items-center gap-2 cursor-pointer">
                <input
                  v-model="manualState[m.key]"
                  type="checkbox"
                  class="rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                />
                <span class="font-semibold text-slate-700">{{ m.label }}</span>
              </label>
            </li>
          </ul>
        </div>

        <!-- 연동 안내 -->
        <div class="bg-blue-50 border border-blue-200 rounded p-3 text-blue-800">
          완료 처리하면 이 프로젝트에 소속된 서버의 장비상태가 <strong>납품완료</strong>로 함께 변경됩니다.
          (RMA 장비는 제외)
        </div>

        <div v-if="blockingReasons.length" class="bg-amber-50 border border-amber-200 rounded p-3 text-amber-800">
          <span class="font-bold">아직 완료할 수 없습니다 — </span>{{ blockingReasons.join(', ') }}
        </div>
      </template>
    </div>

    <template #footer>
      <AppButton variant="secondary" class="text-xs" @click="emit('close')">취소</AppButton>
      <AppButton
        variant="primary"
        class="text-xs"
        :loading="submitting"
        :disabled="loading || blockingReasons.length > 0"
        @click="submitCompletion"
      >
        완료 처리
      </AppButton>
    </template>
  </AppModal>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import api from '@/utils/api'
import { useUiStore } from '@/stores/ui'
import AppButton from '@/components/common/AppButton.vue'
import AppModal from '@/components/common/AppModal.vue'

interface Props {
  isOpen: boolean
  project: any
}

const props = defineProps<Props>()
const emit = defineEmits<{
  (e: 'close'): void
  (e: 'completed'): void
}>()

const uiStore = useUiStore()

const loading = ref(true)
const submitting = ref(false)
const autoChecks = ref<any[]>([])
const manualItems = ref<any[]>([])
const manualState = ref<Record<string, boolean>>({})

// ─── 해당 없음(예외) 처리 ────────────────────────────────────────────────
// 발주 문서가 없는 하도급·구두 발주 건, 품목 없는 기술지원 건 등 검사를 통과할 수 없는
// 정상 사례를 위한 것. 서버도 같은 규칙(사유 최소 길이)으로 다시 검증한다.
const MIN_REASON = 4
const EXEMPT_PLACEHOLDER: Record<string, string> = {
  PO_ATTACHED: '예: 한누리네트웍스 경유 하도급 건으로 발주서 미발행',
  INSPECTION_ATTACHED: '예: 고객사 검수 절차 없음 (메일로 완료 확인)',
  HAS_ITEMS: '예: 호스트네임 변경 기술지원 작업 — 납품 품목 없음',
}
const exemptOn = ref<Record<string, boolean>>({})
const exemptReason = ref<Record<string, string>>({})

function reasonValid(key: string) {
  return (exemptReason.value[key] || '').trim().length >= MIN_REASON
}

/** 화면 표시용 상태: 통과 / 해당 없음 / 미충족 */
function checkState(c: any): 'pass' | 'exempt' | 'fail' {
  if (c.passed) return c.exempted ? 'exempt' : 'pass'
  if (c.exemptable && exemptOn.value[c.key] && reasonValid(c.key)) return 'exempt'
  return 'fail'
}

// 자동 검사는 서버가 판단한 결과를 쓰되, 화면에서 입력 중인 예외는 실시간 반영한다
const blockingReasons = computed(() => {
  const reasons = autoChecks.value.filter(c => checkState(c) === 'fail').map(c => c.label)
  reasons.push(...manualItems.value.filter(m => !manualState.value[m.key]).map(m => m.label))
  return reasons
})

onMounted(() => {
  fetchChecklist()
})

async function fetchChecklist() {
  loading.value = true
  try {
    const res = await api.get(`/projects/${props.project.id}/completion-check`)
    autoChecks.value = res.data.data.auto_checks || []
    manualItems.value = res.data.data.manual_items || []
    manualState.value = Object.fromEntries(
      manualItems.value.map((m: any) => [m.key, !!m.checked]),
    )
  } catch (error) {
    console.error(error)
    uiStore.addToast('체크리스트 조회 실패', 'error')
  } finally {
    loading.value = false
  }
}

async function submitCompletion() {
  submitting.value = true
  try {
    // 미충족 항목 중 '해당 없음'으로 처리한 것만 사유와 함께 보낸다
    const exemptions: Record<string, string> = {}
    for (const c of autoChecks.value) {
      if (!c.passed && c.exemptable && exemptOn.value[c.key] && reasonValid(c.key)) {
        exemptions[c.key] = exemptReason.value[c.key].trim()
      }
    }
    await api.patch(`/projects/${props.project.id}`, {
      status: 'COMPLETED',
      completion_checklist: manualState.value,
      completion_exemptions: exemptions,
    })
    uiStore.addToast('프로젝트를 완료 처리했습니다.', 'success')
    emit('completed')
    emit('close')
  } catch (error: any) {
    console.error(error)
    uiStore.addToast(error.response?.data?.detail || '완료 처리 실패', 'error')
    // 서버 검사에서 걸린 경우 최신 상태를 다시 보여준다
    await fetchChecklist()
  } finally {
    submitting.value = false
  }
}
</script>
