<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { scriptsApi } from '@/api/scripts'
import type { DataScript } from '@/types'

const router = useRouter()

const scripts = ref<DataScript[]>([])
const categories = ref<string[]>([])
const loading = ref(false)
const searchKeyword = ref('')
const selectedCategory = ref('')
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)

const filteredScripts = computed(() => {
  let result = scripts.value

  if (selectedCategory.value) {
    result = result.filter((s) => s.category === selectedCategory.value)
  }

  if (searchKeyword.value) {
    const keyword = searchKeyword.value.toLowerCase()
    result = result.filter(
      (s) =>
        s.script_name.toLowerCase().includes(keyword) ||
        (s.description || '').toLowerCase().includes(keyword)
    )
  }

  return result
})

const paginatedScripts = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  const end = start + pageSize.value
  return filteredScripts.value.slice(start, end)
})

async function loadScripts() {
  loading.value = true
  try {
    const data = await scriptsApi.list({
      page: 1,
      page_size: 2000,
    })
    scripts.value = (data as any).items || []
    total.value = (data as any).total || 0

    // Extract unique categories
    const uniqueCategories = new Set(scripts.value.map((s) => s.category))
    categories.value = Array.from(uniqueCategories).sort()
  } catch (error) {
    console.error('Failed to load scripts:', error)
  } finally {
    loading.value = false
  }
}

function handlePageChange(page: number) {
  currentPage.value = page
}

function handleViewDetail(script: DataScript) {
  router.push(`/scripts/${script.script_id}`)
}

function handleCategoryChange(category: string | number | boolean | undefined) {
  selectedCategory.value = String(category ?? '')
  currentPage.value = 1
}

function handleSearch() {
  currentPage.value = 1
}

onMounted(() => {
  loadScripts()
})
</script>

<template>
  <div class="scripts-view">
    <el-card>
      <template #header>
        <div class="header">
          <span>数据接口</span>
          <el-tag type="info">共 {{ total }} 个接口</el-tag>
        </div>
      </template>

      <div class="content">
        <!-- Category Filter -->
        <div class="category-filter">
          <el-radio-group v-model="selectedCategory" @change="handleCategoryChange">
            <el-radio-button value="">全部</el-radio-button>
            <el-radio-button
              v-for="category in categories"
              :key="category"
              :value="category"
            >
              {{ category }}
            </el-radio-button>
          </el-radio-group>
        </div>

        <!-- Search -->
        <div class="search-bar">
          <el-input
            v-model="searchKeyword"
            placeholder="搜索接口名称或描述"
            clearable
            @input="handleSearch"
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
        </div>

        <!-- Script List -->
        <el-table
          v-loading="loading"
          :data="paginatedScripts"
          style="width: 100%"
          stripe
        >
          <el-table-column prop="script_name" label="接口名称" min-width="200" />
          <el-table-column prop="description" label="描述" show-overflow-tooltip />
          <el-table-column prop="category" label="类别" width="120">
            <template #default="{ row }">
              <el-tag size="small">{{ row.category }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="150" fixed="right">
            <template #default="{ row }">
              <el-button
                type="primary"
                link
                size="small"
                @click="handleViewDetail(row)"
              >
                查看详情
              </el-button>
            </template>
          </el-table-column>
        </el-table>

        <!-- Pagination -->
        <div class="pagination">
          <el-pagination
            :current-page="currentPage"
            :page-size="pageSize"
            :page-sizes="[10, 20, 50, 100]"
            :total="filteredScripts.length"
            layout="total, sizes, prev, pager, next, jumper"
            @current-change="handlePageChange"
            @size-change="(size: number) => { pageSize = size; currentPage = 1 }"
          />
        </div>
      </div>
    </el-card>
  </div>
</template>

<style scoped>
.scripts-view {
  padding: 0;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.category-filter {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.search-bar {
  max-width: 400px;
}

.pagination {
  display: flex;
  justify-content: center;
}
</style>
