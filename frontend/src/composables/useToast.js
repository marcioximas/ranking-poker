import { ref } from 'vue'

const message = ref('')
const visible = ref(false)
let _timer = null

export function useToast() {
  function show(msg, duration = 2800) {
    message.value = msg
    visible.value = true
    clearTimeout(_timer)
    _timer = setTimeout(() => (visible.value = false), duration)
  }
  return { message, visible, show }
}
