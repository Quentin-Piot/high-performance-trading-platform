import { ref, onMounted, onUnmounted } from 'vue'

const currentPath = ref<string>(typeof window !== 'undefined' ? window.location.pathname : '/')

export function useRouter() {
  const navigate = (path: string) => {
    history.pushState(null, '', path)
    currentPath.value = path
  }
  const onPop = () => {
    const path = window.location.pathname
    currentPath.value = path
  }
  onMounted(() => {
    window.addEventListener('popstate', onPop)
  })
  onUnmounted(() => {
    window.removeEventListener('popstate', onPop)
  })
  return { currentPath, navigate }
}