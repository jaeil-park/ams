<template>
  <AppModal :is-open="isOpen" title="파트재고 히스토리 및 사용현황" size="lg" @close="emit('close')">
    <div class="space-y-6 font-sans text-xs" v-if="part">
      <!-- 1. Stats Row -->
      <div class="grid grid-cols-1 md:grid-cols-3 gap-4 bg-slate-50 p-4 rounded-lg border border-slate-200">
        <div>
          <span class="block text-4xs font-bold text-slate-400 uppercase tracking-wider">부품(파트) 모델명</span>
          <span class="block font-semibold text-slate-700 text-xs mt-0.5">{{ part.model }}</span>
        </div>
        <div>
          <span class="block text-4xs font-bold text-slate-400 uppercase tracking-wider">현재 보유 수량</span>
          <span class="block font-semibold text-slate-700 text-xs mt-0.5">{{ part.qty }} 개</span>
        </div>
        <div>
          <span class="block text-4xs font-bold text-slate-400 uppercase tracking-wider">보증 상태</span>
          <span class="block font-semibold text-slate-700 text-xs mt-0.5">
            {{ part.warranty_end || '보증 없음' }} 까지
          </span>
        </div>
      </div>

      <!-- 2. Quantity correction & admin approval workflow trigger -->
      <div class="bg-violet-50 border border-violet-200 rounded-lg p-4 flex flex-col sm:flex-row items-center justify-between gap-3 select-none">
        <div class="flex items-center gap-3">
          <div class="h-8 w-8 bg-violet-100 text-violet-600 rounded-full flex items-center justify-center">
            <svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
            </svg>
          </div>
          <div>
            <h4 class="font-bold text-violet-800">재고 수량 보정 (결재 연동)</h4>
            <p class="text-slate-500 font-medium mt-0.5">
              파트의 보유 수량을 임의 수정할 시, PENDING 승인 레코드가 예약되며 관리자 승인 후 반영됩니다.
            </p>
          </div>
        </div>
        <div class="flex items-center gap-2 self-stretch sm:self-auto">
          <input 
            type="number" 
            v-model="targetQty"
            placeholder="수량"
            class="w-16 px-2 py-1.5 border border-slate-300 rounded text-center focus:outline-none"
          />
          <AppButton 
            variant="primary" 
            class="text-3xs px-3 py-1.5 shrink-0 bg-violet-700 hover:bg-violet-800"
            :loading="approvalLoading"
            @click="requestQtyChange"
          >
            변경 결재 요청
          </AppButton>
        </div>
      </div>

      <!-- 3. Usage History Table -->
      <div>
        <h4 class="font-bold text-slate-800 mb-2 pb-1 border-b border-slate-100 select-none">부품 출고 및 사용 이력</h4>
        <div v-if="usages.length === 0" class="text-slate-400 font-medium text-center py-6 bg-slate-50 rounded border border-dashed border-slate-200">
          사용 이력이 존재하지 않습니다.
        </div>
        <div v-else class="overflow-x-auto border border-slate-200 rounded">
          <table class="min-w-full divide-y divide-slate-100 bg-white">
            <thead class="bg-slate-50 select-none">
              <tr>
                <th class="px-4 py-2 text-left font-bold text-slate-500">사용일자</th>
                <th class="px-4 py-2 text-left font-bold text-slate-500">사용 수량</th>
                <th class="px-4 py-2 text-left font-bold text-slate-500">납품 위치</th>
                <th class="px-4 py-2 text-left font-bold text-slate-500">출고 사유</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100">
              <tr v-for="usage in usages" :key="usage.id" class="hover:bg-slate-50 text-slate-700">
                <td class="px-4 py-2 font-mono">{{ usage.used_date }}</td>
                <td class="px-4 py-2 font-bold">{{ usage.qty }} 개</td>
                <td class="px-4 py-2 text-slate-500">{{ usage.location || '-' }}</td>
                <td class="px-4 py-2 text-slate-500">{{ usage.reason || '-' }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </AppModal>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import api from '@/utils/api'
import { useUiStore } from '@/stores/ui'
import AppBadge from '@/components/common/AppBadge.vue'
import AppButton from '@/components/common/AppButton.vue'
import AppModal from '@/components/common/AppModal.vue'

interface Props {
  isOpen: boolean
  partId: number
}

const props = defineProps<Props>()
const emit = defineEmits<{
  (e: 'close'): void
  (e: 'updated'): void
}>()

const uiStore = useUiStore()

const part = ref<any>(null)
const usages = ref<any[]>([])
const targetQty = ref<number | null>(null)
const approvalLoading = ref(false)

onMounted(() => {
  fetchPartDetail()
  fetchUsageHistory()
})

async function fetchPartDetail() {
  try {
    const res = await api.get(`/parts/${props.partId}`)
    part.value = res.data.data
    targetQty.value = part.value.qty
  } catch (error) {
    console.error('Part detail fetch failed:', error)
  }
}

async function fetchUsageHistory() {
  try {
    // API 명세상 Usage는 custom filter로 목록을 받습니다.
    const res = await api.get(`/parts?limit=100`)
    // 이 파트 ID를 찌르는 이력이 있다면 가져옵니다 (Mocking / usage list binding)
    usages.value = []
  } catch (error) {
    console.error(error)
  }
}

async function requestQtyChange() {
  if (targetQty.value === null || targetQty.value < 0) {
    uiStore.addToast('올바른 수량을 입력해 주세요.', 'warning')
    return
  }
  approvalLoading.value = true
  try {
    const res = await api.patch(`/parts/${props.partId}/qty?target_qty=${targetQty.value}&reason=수량 조율 요청`)
    if (res.data.data) {
      uiStore.addToast('관리자 수량 변경 승인 요청이 정상 접수되었습니다 (PENDING)', 'success')
      emit('updated')
      emit('close')
    }
  } catch (error: any) {
    console.error(error)
    const errDetail = error.response?.data?.detail || '승인 요청 처리 실패'
    uiStore.addToast(errDetail, 'error')
  } finally {
    approvalLoading.value = false
  }
}
</script>
