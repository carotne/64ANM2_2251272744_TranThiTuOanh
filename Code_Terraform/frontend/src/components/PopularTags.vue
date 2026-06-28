<template>
  <p>Popular Tags</p>

  <div class="tag-list">
    <span
      v-if="tagsError"
      class="tag-default tag-pill"
    >
      unavailable
    </span>

    <AppLink
      v-for="tag in tags"
      :key="tag"
      class="tag-pill tag-default"
      :aria-label="tag"
      name="tag"
      :params="{ tag }"
    >
      {{ tag }}
    </AppLink>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useTags } from 'src/composable/use-tags'

const { tags, fetchTags } = useTags()
const tagsError = ref(false)

onMounted(async () => {
  try {
    tagsError.value = false
    await fetchTags()
  }
  catch (error) {
    tagsError.value = true
    console.error('Unable to load tags', error)
  }
})
</script>
