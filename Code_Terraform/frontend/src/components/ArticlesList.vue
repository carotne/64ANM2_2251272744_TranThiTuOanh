<template>
  <ArticlesListNavigation
    v-bind="$attrs"
    :tag="tag"
    :username="username"
  />

  <div
    v-if="articlesError"
    class="article-preview"
  >
    Unable to load articles. Please refresh the page.
  </div>

  <div
    v-else-if="articlesDownloading"
    class="article-preview"
  >
    Articles are downloading...
  </div>

  <div
    v-else-if="articles.length === 0"
    class="article-preview"
  >
    No articles are here... yet.
  </div>

  <template v-else>
    <ArticlesListArticlePreview
      v-for="(article, index) in articles"
      :key="article.slug"
      :article="article"
      @update="newArticle => updateArticle(index, newArticle)"
    />

    <AppPagination
      :count="articlesCount"
      :page="page"
      @page-change="changePage"
    />
  </template>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useArticles } from 'src/composable/use-articles'
import AppPagination from './AppPagination.vue'
import ArticlesListArticlePreview from './ArticlesListArticlePreview.vue'
import ArticlesListNavigation from './ArticlesListNavigation.vue'

const {
  fetchArticles,
  articlesDownloading,
  articlesError,
  articlesCount,
  articles,
  updateArticle,
  page,
  changePage,
  tag,
  username,
} = useArticles()

onMounted(fetchArticles)
</script>
