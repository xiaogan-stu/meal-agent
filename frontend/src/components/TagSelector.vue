<script setup lang="ts">
const props = defineProps<{
  label: string
  options: string[]
  modelValue: string[]
  required?: boolean
}>()

const emit = defineEmits<{
  'update:modelValue': [value: string[]]
}>()

function toggle(option: string): void {
  const next = props.modelValue.includes(option)
    ? props.modelValue.filter((item) => item !== option)
    : [...props.modelValue, option]
  emit('update:modelValue', next)
}
</script>

<template>
  <fieldset class="tag-field">
    <legend>
      {{ label }}
      <span v-if="required" class="required-mark">必选</span>
    </legend>
    <div class="tag-options">
      <button
        v-for="option in options"
        :key="option"
        class="tag-option"
        :class="{ selected: modelValue.includes(option) }"
        type="button"
        :aria-pressed="modelValue.includes(option)"
        @click="toggle(option)"
      >
        {{ option }}
      </button>
    </div>
  </fieldset>
</template>