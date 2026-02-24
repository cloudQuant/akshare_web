<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { tablesApi } from '@/api/tables'
import type { DataTable } from '@/types'

const router = useRouter()

const tables = ref<DataTable[]>([])
const loading = ref(false)
const searchKeyword = ref('')
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)

const filteredTables = computed(() => {
  if (!searchKeyword.value) return tables.value
  const keyword = searchKeyword.value.toLowerCase()
  return tables.value.filter((t) =>
    t.table_name.toLowerCase().includes(keyword)
  )
})

async function loadTables() {
  loading.value = true
  try {
    const data = await tablesApi.list({
      page: currentPage.value,
      page_size: pageSize.value,
    })
    tables.value = (data as any).items || []
    total.value = (data as any).total || 0
  } catch (error) {
    console.error('Failed to load tables:', error)
  } finally {
    loading.value = false
  }
}

function handleViewDetail(table: DataTable) {
  router.push(`/tables/${table.id}`)
}

function handlePageChange(page: number) {
  currentPage.value = page
  loadTables()
}

onMounted(() => {
  loadTables()
})
</script>

<template>
  <div class="tables-view">
    <el-card>
      <template #header>
        <div class="header">
          <span>数据表</span>
          <el-tag type="info">共 {{ total }} 个表</el-tag>
        </div>
      </template>

      <div class="content">
        <div class="search-bar">
          <el-input
            v-model="searchKeyword"
            placeholder="搜索表名"
            clearable
            style="max-width: 400px"
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
        </div>

        <el-table
          v-loading="loading"
          :data="filteredTables"
          style="width: 100%"
          stripe
        >
          <el-table-column prop="table_name" label="表名" min-width="200" />
          <el-table-column prop="row_count" label="行数" width="120">
            <template #default="{ row }">
              {{ row.row_count?.toLocaleString() || 0 }}
            </template>
          </el-table-column>
          <el-table-column prop="created_at" label="创建时间" width="180">
            <template #default="{ row }">
              {{ new Date(row.created_at).toLocaleString() }}
            </template>
          </el-table-column>
          <el-table-column prop="updated_at" label="更新时间" width="180">
            <template #default="{ row }">
              {{ new Date(row.updated_at).toLocaleString() }}
            </template>
          </el-table-column>
          <el-table-column label="操作" width="120" fixed="right">
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

        <div class="pagination">
          <el-pagination
            :current-page="currentPage"
            :page-size="pageSize"
            :total="total"
            layout="total, prev, pager, next"
            @current-change="handlePageChange"
          />
        </div>
      </div>
    </el-card>
  </div>
</template>


<style scoped>
.tables-view {
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

.search-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.pagination {
  display: flex;
  justify-content: center;
}
</style>
