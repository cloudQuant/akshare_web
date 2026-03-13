import { ref, shallowRef, type ShallowRef } from 'vue'
import { getApiErrorMessage } from '@/utils/error'

export interface UseAsyncOptions<T> {
  immediate?: boolean
  showLoading?: boolean
  showError?: boolean
  resetOnError?: boolean
}

export function useAsync<T>(
  asyncFn: () => Promise<T>,
  options: UseAsyncOptions<T> = {}
): {
  const data = shallowRef<T | null>(null)
  const loading = ref(false)
  const error = shallowRef<string | null>(null)
  const isError = shallowRef<boolean>(false)

  async function execute() {
    loading.value = true
    error.value = null
    isError.value = false

    try {
      const result = await asyncFn()
      data.value = result
      return result
    } catch (e) {
      const errorMessage = e instanceof Error ? e.message : getApiErrorMessage(e)
      error.value = errorMessage
      isError.value = true
      if (options.onError) {
        console.error(errorMessage)
      }
      return null
    } finally {
      loading.value = false
    }
  }

  function reset() {
    data.value = null
    loading.value = false
    error.value = null
    isError.value = false
  }

  return {
    data: shallowRef(data),
    loading: shallowRef(loading),
    error: shallowRef(error),
    isError: shallowRef(isError),
    execute,
    reset,
  }
}
