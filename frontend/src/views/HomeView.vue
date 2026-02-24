<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { dataApi } from '@/api/data'
import { scriptsApi } from '@/api/scripts'
import type { ExecutionStats, DataScript } from '@/types'

const stats = ref<ExecutionStats | null>(null)
const recentScripts = ref<DataScript[]>([])
const loading = ref(false)

async function loadStats() {
  try {
    const [statsData, scriptsData] = await Promise.all([
      dataApi.getStats().catch(() => null),
      scriptsApi.list({ page: 1, page_size: 5 }).catch(() => null),
    ])
    if (statsData) stats.value = statsData
    if (scriptsData?.items) recentScripts.value = scriptsData.items
  } catch (error) {
    console.error('Failed to load stats:', error)
  }
}

onMounted(() => {
  loadStats()
})
</script>

<template>
  <div class="home-view">
    <el-row :gutter="20">
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-content">
            <el-icon class="stat-icon primary"><Document /></el-icon>
            <div class="stat-info">
              <div class="stat-value">{{ stats?.total_count || 0 }}</div>
              <div class="stat-label">总执行次数</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-content">
            <el-icon class="stat-icon success"><CircleCheck /></el-icon>
            <div class="stat-info">
              <div class="stat-value">{{ stats?.success_count || 0 }}</div>
              <div class="stat-label">成功次数</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-content">
            <el-icon class="stat-icon danger"><CircleClose /></el-icon>
            <div class="stat-info">
              <div class="stat-value">{{ stats?.failed_count || 0 }}</div>
              <div class="stat-label">失败次数</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-content">
            <el-icon class="stat-icon warning"><TrendCharts /></el-icon>
            <div class="stat-info">
              <div class="stat-value">
                {{ stats?.success_rate ? (stats.success_rate * 100).toFixed(1) : 0 }}%
              </div>
              <div class="stat-label">成功率</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" style="margin-top: 20px">
      <el-col :span="12">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>快捷操作</span>
            </div>
          </template>
          <div class="quick-actions">
            <el-button type="primary" @click="$router.push('/scripts')">
              <el-icon><DataLine /></el-icon>
              浏览数据接口
            </el-button>
            <el-button type="success" @click="$router.push('/tasks')">
              <el-icon><Timer /></el-icon>
              创建定时任务
            </el-button>
            <el-button type="info" @click="$router.push('/tables')">
              <el-icon><Grid /></el-icon>
              查看数据表
            </el-button>
            <el-button @click="$router.push('/executions')">
              <el-icon><Document /></el-icon>
              执行记录
            </el-button>
          </div>
        </el-card>
      </el-col>

      <el-col :span="12">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>最近使用的接口</span>
            </div>
          </template>
          <el-empty v-if="recentScripts.length === 0" description="暂无数据" />
          <el-table v-else :data="recentScripts" style="width: 100%">
            <el-table-column prop="script_name" label="接口名称" />
            <el-table-column prop="category" label="类别" width="120" />
            <el-table-column label="操作" width="100">
              <template #default="{ row }">
                <el-button
                  type="primary"
                  link
                  size="small"
                  @click="$router.push(`/scripts/${row.script_id}`)"
                >
                  查看
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<style scoped>
.home-view {
  padding: 0;
}

.stat-card {
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s;
}

.stat-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.stat-content {
  display: flex;
  align-items: center;
  gap: 16px;
}

.stat-icon {
  width: 48px;
  height: 48px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
}

.stat-icon.primary {
  background-color: #e6f7ff;
  color: #1890ff;
}

.stat-icon.success {
  background-color: #f6ffed;
  color: #52c41a;
}

.stat-icon.danger {
  background-color: #fff1f0;
  color: #ff4d4f;
}

.stat-icon.warning {
  background-color: #fffbe6;
  color: #faad14;
}

.stat-info {
  flex: 1;
}

.stat-value {
  font-size: 24px;
  font-weight: bold;
  color: #303133;
}

.stat-label {
  font-size: 14px;
  color: #909399;
  margin-top: 4px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.quick-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.quick-actions .el-button {
  flex: 1;
  min-width: 140px;
}
</style>
