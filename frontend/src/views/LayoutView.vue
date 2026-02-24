<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const isCollapse = ref(false)
const activeMenu = computed(() => route.path)

const menuItems = computed(() => {
  const items = [
    { index: '/', name: '首页', icon: 'HomeFilled' },
    { index: '/scripts', name: '数据接口', icon: 'DataLine' },
    { index: '/tasks', name: '定时任务', icon: 'Timer' },
    { index: '/executions', name: '执行记录', icon: 'Document' },
    { index: '/tables', name: '数据表', icon: 'Grid' },
  ]

  if (authStore.isAdmin) {
    items.push({ index: '/admin/interfaces', name: '接口管理', icon: 'Management' })
    items.push({ index: '/users', name: '用户管理', icon: 'User' })
    items.push({ index: '/settings', name: '设置', icon: 'Setting' })
  }

  return items
})

function handleLogout() {
  authStore.logout()
  router.push('/login')
}

function toggleCollapse() {
  isCollapse.value = !isCollapse.value
}
</script>

<template>
  <el-container class="layout-container">
    <!-- Sidebar -->
    <el-aside :width="isCollapse ? '64px' : '200px'" class="sidebar">
      <div class="logo">
        <span v-if="!isCollapse">akshare_web</span>
        <span v-else>ak</span>
      </div>
      <el-menu
        :default-active="activeMenu"
        :collapse="isCollapse"
        :collapse-transition="false"
        router
      >
        <el-menu-item
          v-for="item in menuItems"
          :key="item.index"
          :index="item.index"
        >
          <el-icon><component :is="item.icon" /></el-icon>
          <template #title>{{ item.name }}</template>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <!-- Main Content -->
    <el-container>
      <el-header class="header">
        <div class="header-left">
          <el-button
            :icon="isCollapse ? 'Expand' : 'Fold'"
            text
            @click="toggleCollapse"
          />
        </div>
        <div class="header-right">
          <el-dropdown>
            <span class="user-dropdown">
              <el-avatar :size="32" :icon="'UserFilled'" />
              <span class="username">{{ authStore.user?.email }}</span>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item disabled>
                  角色: {{ authStore.user?.role }}
                </el-dropdown-item>
                <el-dropdown-item divided @click="handleLogout">
                  退出登录
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>

      <el-main class="main-content">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<style scoped>
.layout-container {
  height: 100vh;
}

.sidebar {
  background-color: #001529;
  transition: width 0.3s;
}

.logo {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 18px;
  font-weight: bold;
  border-bottom: 1px solid #002140;
}

.el-menu {
  border-right: none;
  background-color: #001529;
}

.el-menu-item {
  color: rgba(255, 255, 255, 0.65);
}

.el-menu-item:hover {
  background-color: #1890ff !important;
  color: #fff;
}

.el-menu-item.is-active {
  background-color: #1890ff !important;
  color: #fff;
}

.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid #f0f0f0;
  padding: 0 20px;
}

.header-left {
  display: flex;
  align-items: center;
}

.header-right {
  display: flex;
  align-items: center;
}

.user-dropdown {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}

.username {
  font-size: 14px;
}

.main-content {
  background-color: #f0f2f5;
  overflow-y: auto;
}
</style>
