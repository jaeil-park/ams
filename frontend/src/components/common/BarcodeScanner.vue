<template>
  <div class="barcode-scanner">
    <!-- 카메라 지원 여부에 따라 분기 -->
    <div v-if="!cameraSupported" class="fallback-input">
      <p class="text-xs text-amber-600 font-medium mb-2 flex items-center gap-1.5">
        <svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
        </svg>
        카메라를 사용할 수 없습니다. 직접 입력해주세요.
      </p>
      <div class="flex gap-2">
        <input
          v-model="manualInput"
          type="text"
          placeholder="시리얼 태그 직접 입력"
          class="flex-1 border border-slate-300 rounded px-3 py-2 text-xs focus:outline-none focus:ring-2 focus:ring-blue-500"
          @keyup.enter="emitManual"
        />
        <button
          type="button"
          class="px-3 py-2 bg-blue-600 text-white rounded text-xs font-semibold hover:bg-blue-700 transition-colors"
          @click="emitManual"
        >
          확인
        </button>
      </div>
    </div>

    <div v-else>
      <!-- 스캔 화면 -->
      <div v-if="isScanning" class="scanner-viewport relative">
        <video
          ref="videoEl"
          class="w-full rounded-lg border border-slate-300"
          :class="{ 'opacity-0 h-0': !isScanning }"
          autoplay
          playsinline
          muted
        />
        <canvas ref="canvasEl" class="hidden" />

        <!-- 스캔 오버레이 -->
        <div class="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
          <div class="border-2 border-blue-400 rounded-lg w-48 h-32 relative">
            <span class="absolute -top-0.5 -left-0.5 h-4 w-4 border-t-2 border-l-2 border-blue-500 rounded-tl" />
            <span class="absolute -top-0.5 -right-0.5 h-4 w-4 border-t-2 border-r-2 border-blue-500 rounded-tr" />
            <span class="absolute -bottom-0.5 -left-0.5 h-4 w-4 border-b-2 border-l-2 border-blue-500 rounded-bl" />
            <span class="absolute -bottom-0.5 -right-0.5 h-4 w-4 border-b-2 border-r-2 border-blue-500 rounded-br" />
            <!-- 스캔 레이저 라인 -->
            <div class="scan-line absolute left-0 right-0 h-0.5 bg-blue-400 opacity-75" />
          </div>
          <p class="mt-3 text-white text-xs font-semibold drop-shadow-lg">바코드를 사각형 안에 위치시켜주세요</p>
        </div>

        <!-- 닫기 버튼 -->
        <button
          type="button"
          class="absolute top-2 right-2 bg-black/50 text-white rounded-full p-1.5 hover:bg-black/70 transition-colors"
          @click="stopScan"
        >
          <svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      <!-- 스캔 시작 버튼 -->
      <div v-if="!isScanning" class="flex gap-2 items-center">
        <button
          type="button"
          class="flex items-center gap-2 px-3 py-2 bg-blue-600 text-white rounded text-xs font-semibold hover:bg-blue-700 transition-colors"
          @click="startScan"
        >
          <svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z" />
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 13a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
          카메라로 스캔
        </button>
        <span class="text-slate-400 text-xs">또는</span>
        <div class="flex gap-2 flex-1">
          <input
            v-model="manualInput"
            type="text"
            placeholder="시리얼 직접 입력"
            class="flex-1 border border-slate-300 rounded px-3 py-2 text-xs focus:outline-none focus:ring-2 focus:ring-blue-500"
            @keyup.enter="emitManual"
          />
          <button
            type="button"
            class="px-3 py-2 bg-slate-200 text-slate-700 rounded text-xs font-semibold hover:bg-slate-300 transition-colors"
            @click="emitManual"
          >
            확인
          </button>
        </div>
      </div>

      <!-- 스캔 성공 피드백 -->
      <div
        v-if="lastScanned"
        class="mt-2 flex items-center gap-2 px-3 py-2 bg-emerald-50 border border-emerald-200 rounded text-xs text-emerald-700 font-semibold"
      >
        <svg class="h-4 w-4 text-emerald-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
        </svg>
        스캔 완료: {{ lastScanned }}
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onUnmounted } from 'vue'
import jsQR from 'jsqr'

const emit = defineEmits<{
  (e: 'scanned', value: string): void
}>()

const videoEl = ref<HTMLVideoElement | null>(null)
const canvasEl = ref<HTMLCanvasElement | null>(null)
const isScanning = ref(false)
const cameraSupported = ref(!!navigator.mediaDevices?.getUserMedia)
const manualInput = ref('')
const lastScanned = ref('')

let stream: MediaStream | null = null
let animFrameId: number | null = null

async function startScan() {
  try {
    stream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: 'environment' } // 후면 카메라 우선
    })
    isScanning.value = true

    // DOM 업데이트 후 video에 연결
    await new Promise(r => setTimeout(r, 100))
    if (videoEl.value) {
      videoEl.value.srcObject = stream
      videoEl.value.play()
      requestTick()
    }
  } catch (err) {
    console.error('카메라 접근 실패:', err)
    cameraSupported.value = false
  }
}

function requestTick() {
  animFrameId = requestAnimationFrame(scanFrame)
}

function scanFrame() {
  if (!videoEl.value || !canvasEl.value || !isScanning.value) return

  const video = videoEl.value
  if (video.readyState !== video.HAVE_ENOUGH_DATA) {
    requestTick()
    return
  }

  const canvas = canvasEl.value
  const ctx = canvas.getContext('2d')
  if (!ctx) return

  canvas.width = video.videoWidth
  canvas.height = video.videoHeight
  ctx.drawImage(video, 0, 0, canvas.width, canvas.height)

  const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height)
  const code = jsQR(imageData.data, imageData.width, imageData.height, {
    inversionAttempts: 'dontInvert',
  })

  if (code) {
    const result = code.data
    lastScanned.value = result
    emit('scanned', result)
    stopScan()
    return
  }

  requestTick()
}

function stopScan() {
  isScanning.value = false
  if (animFrameId !== null) {
    cancelAnimationFrame(animFrameId)
    animFrameId = null
  }
  if (stream) {
    stream.getTracks().forEach(t => t.stop())
    stream = null
  }
}

function emitManual() {
  const val = manualInput.value.trim()
  if (!val) return
  lastScanned.value = val
  emit('scanned', val)
  manualInput.value = ''
}

onUnmounted(() => {
  stopScan()
})
</script>

<style scoped>
.scan-line {
  animation: scan 2s linear infinite;
  top: 0;
}

@keyframes scan {
  0% { top: 0; }
  50% { top: calc(100% - 2px); }
  100% { top: 0; }
}
</style>
