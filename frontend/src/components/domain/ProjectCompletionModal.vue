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
              class="flex items-center gap-2 px-3 py-2"
              :class="c.passed ? 'bg-white' : 'bg-red-50'"
            >
              <svg v-if="c.passed" class="h-4 w-4 text-emerald-600 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 13l4 4L19 7" />
              </svg>
              <svg v-else class="h-4 w-4 text-red-500 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M6 18L18 6M6 6l12 12" />
              </svg>
              <span class="font-semibold" :class="c.passed ? 'text-slate-700' : 'text-red-700'">{{ c.label }}</span>
              <span class="ml-auto text-slate-400 text-right">{{ c.detail }}</span>
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

// 자동 검사는 서버가 판단한 결과를 그대로 쓰고, 수기 항목만 화면에서 실시간 반영한다
const blockingReasons = computed(() => {
  const reasons = autoChecks.value.filter(c => !c.passed).map(c => c.label)
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
    await api.patch(`/projects/${props.project.id}`, {
      status: 'COMPLETED',
      completion_checklist: manualState.value,
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
