<template>
  <div class="space-y-4">
    <div class="flex items-center justify-between">
      <h3 class="text-lg font-semibold text-foreground">{{ t('todo.title') }}</h3>
      <Button 
        variant="outline" 
        size="sm" 
        class="flex items-center gap-2"
        @click="addTodo"
      >
        <Plus class="size-4" />
        {{ t('todo.add') }}
      </Button>
    </div>
    <div class="space-y-2">
      <div
        v-for="todo in todos"
        :key="todo.id"
        class="flex items-center gap-3 p-3 rounded-lg border bg-card hover:bg-accent/50 transition-colors"
      >
        <Checkbox
          :id="todo.id"
          :checked="todo.completed"
          @update:checked="toggleTodo(todo.id)"
        />
        <div class="flex-1 min-w-0">
          <label
            :for="todo.id"
            :class="[
              'text-sm cursor-pointer',
              todo.completed ? 'line-through text-muted-foreground' : 'text-foreground'
            ]"
          >
            {{ todo.text }}
          </label>
          <div class="flex items-center gap-2 mt-1">
            <Badge
              :variant="getPriorityVariant(todo.priority)"
              class="text-xs"
            >
              {{ t(`todo.priority.${todo.priority}`) }}
            </Badge>
            <span class="text-xs text-muted-foreground">
              {{ formatDate(todo.createdAt) }}
            </span>
          </div>
        </div>
        <Button
          variant="ghost"
          size="sm"
          class="text-muted-foreground hover:text-destructive"
          @click="removeTodo(todo.id)"
        >
          <Trash2 class="size-4" />
        </Button>
      </div>
      <div v-if="todos.length === 0" class="text-center py-8 text-muted-foreground">
        <CheckCircle class="size-8 mx-auto mb-2 opacity-50" />
        <p>{{ t('todo.empty') }}</p>
      </div>
    </div>
    <Dialog v-model:open="showAddDialog">
      <DialogContent class="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>{{ t('todo.add_new') }}</DialogTitle>
        </DialogHeader>
        <div class="space-y-4">
          <div>
            <Label for="todo-text">{{ t('todo.task') }}</Label>
            <Input
              id="todo-text"
              v-model="newTodoText"
              :placeholder="t('todo.task_placeholder')"
              @keyup.enter="submitTodo"
            />
          </div>
          <div>
            <Label for="todo-priority">{{ t('todo.priority.label') }}</Label>
            <Select v-model="newTodoPriority">
              <SelectTrigger>
                <SelectValue :placeholder="t('todo.priority.select')" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="low">{{ t('todo.priority.low') }}</SelectItem>
                <SelectItem value="medium">{{ t('todo.priority.medium') }}</SelectItem>
                <SelectItem value="high">{{ t('todo.priority.high') }}</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" @click="showAddDialog = false">
            {{ t('common.cancel') }}
          </Button>
          <Button :disabled="!newTodoText.trim()" @click="submitTodo">
            {{ t('todo.add') }}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  </div>
</template>
<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Plus, Trash2, CheckCircle } from 'lucide-vue-next'
const { t } = useI18n()
interface Todo {
  id: string
  text: string
  completed: boolean
  priority: 'low' | 'medium' | 'high'
  createdAt: Date
}
const todos = ref<Todo[]>([
  {
    id: '1',
    text: 'Optimiser les performances des backtests Monte Carlo',
    completed: false,
    priority: 'high',
    createdAt: new Date('2024-01-15')
  },
  {
    id: '2', 
    text: 'Ajouter plus de stratégies de trading',
    completed: false,
    priority: 'medium',
    createdAt: new Date('2024-01-16')
  },
  {
    id: '3',
    text: 'Améliorer la documentation utilisateur',
    completed: true,
    priority: 'low',
    createdAt: new Date('2024-01-14')
  }
])
const showAddDialog = ref(false)
const newTodoText = ref('')
const newTodoPriority = ref<'low' | 'medium' | 'high'>('medium')
const addTodo = () => {
  showAddDialog.value = true
  newTodoText.value = ''
  newTodoPriority.value = 'medium'
}
const submitTodo = () => {
  if (!newTodoText.value.trim()) return
  const newTodo: Todo = {
    id: Date.now().toString(),
    text: newTodoText.value.trim(),
    completed: false,
    priority: newTodoPriority.value,
    createdAt: new Date()
  }
  todos.value.unshift(newTodo)
  showAddDialog.value = false
}
const toggleTodo = (id: string) => {
  const todo = todos.value.find(t => t.id === id)
  if (todo) {
    todo.completed = !todo.completed
  }
}
const removeTodo = (id: string) => {
  const index = todos.value.findIndex(t => t.id === id)
  if (index > -1) {
    todos.value.splice(index, 1)
  }
}
const getPriorityVariant = (priority: string) => {
  switch (priority) {
    case 'high': return 'destructive'
    case 'medium': return 'default'
    case 'low': return 'secondary'
    default: return 'default'
  }
}
const formatDate = (date: Date) => {
  return new Intl.DateTimeFormat('fr-FR', {
    day: 'numeric',
    month: 'short'
  }).format(date)
}
</script>