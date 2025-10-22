<template>
  <div class="space-y-2">
    <Label class="text-sm font-medium flex items-center gap-2">
      <div class="rounded-lg bg-trading-blue/10 p-1.5 text-trading-blue">
        <Upload class="size-3.5" />
      </div>
      {{ t('simulate.form.labels.csv_file') }}
    </Label>
    <div
      class="group relative overflow-hidden rounded-xl border-2 border-dashed p-4 text-sm transition-all duration-300 cursor-pointer"
      :class="[
        dragActive 
          ? 'border-trading-blue bg-gradient-to-br from-trading-blue/5 via-trading-blue/10 to-trading-purple/5 shadow-soft' 
          : 'border-border hover:border-trading-blue/50 hover:bg-gradient-to-br hover:from-secondary/30 hover:to-accent/20',
        'text-muted-foreground hover:text-foreground'
      ]"
      @click="onZoneClick"
      @dragenter="onDragEnter"
      @dragover="onDragOver"
      @dragleave="onDragLeave"
      @drop="onDrop"
    >
      <!-- Animated background effect -->
      <div class="absolute inset-0 bg-gradient-to-r from-transparent via-white/5 to-transparent -translate-x-full group-hover:translate-x-full transition-transform duration-1000"></div>
      
      <input ref="inputEl" type="file" accept=".csv" multiple class="hidden" @change="onFileChange" />
      
      <div class="relative z-10 flex flex-col items-center gap-3">
        <div class="rounded-full bg-secondary/50 p-3 group-hover:bg-trading-blue/10 transition-colors">
          <FileSpreadsheet class="size-6 text-muted-foreground group-hover:text-trading-blue transition-colors" />
        </div>
        <div class="text-center">
          <p class="font-medium">{{ t('simulate.form.csv.drop_hint') }}</p>
          <p class="text-xs text-muted-foreground mt-1">{{ t('simulate.form.csv.max_files') }}</p>
          <div v-if="selectedFiles.length > 0" class="mt-3 space-y-2">
            <p class="text-xs text-trading-green font-medium flex items-center justify-center gap-2">
              <CheckCircle class="size-4" />
              {{ selectedFiles.length }} {{ t('simulate.form.csv.files_selected') }}
            </p>
            <div class="max-h-32 overflow-y-auto space-y-1">
              <div
v-for="(file, index) in selectedFiles" :key="index" 
                   class="flex items-center justify-between bg-secondary/30 rounded-lg px-3 py-2 text-xs">
                <span class="truncate flex-1">{{ file.name }}</span>
                <button
class="ml-2 p-1 hover:bg-red-100 rounded-full transition-colors" 
                        @click.stop="removeFile(index)">
                  <X class="size-3 text-red-500" />
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { Label } from '@/components/ui/label'
import { Upload, FileSpreadsheet, CheckCircle, X } from 'lucide-vue-next'

interface Props {
  selectedFiles: File[]
  error?: string | null
}

interface Emits {
  (e: 'update:selectedFiles', files: File[]): void
  (e: 'update:error', error: string | null): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const { t } = useI18n()

const dragActive = ref(false)
const inputEl = ref<HTMLInputElement | null>(null)

function onFileChange(e: Event) {
  const input = e.target as HTMLInputElement
  const files = Array.from(input.files || [])
  addFiles(files)
}

function addFiles(files: File[]) {
  emit('update:error', null)
  const validFiles = files.filter(f => {
    if (!isCsvFile(f)) {
      emit('update:error', t('errors.invalid_csv'))
      return false
    }
    return true
  })
  
  const newFiles = [...props.selectedFiles, ...validFiles]
  if (newFiles.length > 10) {
    emit('update:error', 'Maximum 10 files allowed')
    return
  }
  
  emit('update:selectedFiles', newFiles)
}

function removeFile(index: number) {
  const newFiles = props.selectedFiles.filter((_, i) => i !== index)
  emit('update:selectedFiles', newFiles)
}

function isCsvFile(f: File) {
  // Certains navigateurs remettent un type mimé incohérent pour CSV, on tolère l'extension
  return f.type === 'text/csv' || f.name.toLowerCase().endsWith('.csv')
}

function onZoneClick() {
  inputEl.value?.click()
}

function onDragOver(e: DragEvent) {
  e.preventDefault()
  dragActive.value = true
}

function onDragEnter(e: DragEvent) {
  e.preventDefault()
  dragActive.value = true
}

function onDragLeave(e: DragEvent) {
  e.preventDefault()
  dragActive.value = false
}

function onDrop(e: DragEvent) {
  e.preventDefault()
  dragActive.value = false
  const files = Array.from(e.dataTransfer?.files || [])
  addFiles(files)
}
</script>