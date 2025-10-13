<script setup lang="ts">
import TopNav from '@/components/common/TopNav.vue'

interface Props {
  /** Classes CSS additionnelles pour le main */
  mainClass?: string
  /** Classes CSS additionnelles pour le container */
  containerClass?: string
  /** Désactiver l'animation fade-in */
  noAnimation?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  mainClass: '',
  containerClass: 'space-y-6 sm:space-y-10',
  noAnimation: false
})
</script>

<template>
  <main 
    :class="[
      'container mx-auto px-4 sm:px-6 py-6 sm:py-10',
      props.containerClass,
      { 'animate-fade-in': !props.noAnimation },
      props.mainClass
    ]"
  >
    <TopNav />
    
    <!-- Slot pour le contenu spécifique de chaque page -->
    <slot />
  </main>
</template>