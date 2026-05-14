<script setup>
const props = defineProps({
  mode: {
    type: String,
    required: true,
  },
  modelValue: {
    type: Object,
    required: true,
  },
  configured: {
    type: Object,
    required: true,
  },
});

const emit = defineEmits(["update:field"]);

function update(field, event) {
  emit("update:field", field, event.target.value);
}

function placeholder(name, configured) {
  return configured ? `Enter a new ${name} key only if you want to replace the stored one` : "Paste a new API key";
}
</script>

<template>
  <section
    v-if="['openai', 'gemini', 'anthropic'].includes(mode)"
    class="rounded-lg border border-slate-200 bg-white p-5 shadow-sm"
  >
    <div class="mb-5">
      <p class="text-xs font-semibold uppercase tracking-wide text-slate-500">Cloud credentials</p>
      <h2 class="mt-1 text-xl font-semibold text-slate-950">Provider access</h2>
      <p class="mt-1 max-w-2xl text-sm leading-6 text-slate-600">
        Stored keys are never shown. Leave a key field blank to keep the current saved value.
      </p>
    </div>

    <div v-if="mode === 'openai'" class="max-w-2xl">
      <label class="block">
        <span class="text-sm font-medium text-slate-700">OpenAI API key</span>
        <input
          :value="props.modelValue.openaiKey"
          type="password"
          autocomplete="off"
          class="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 font-mono text-sm text-slate-950 shadow-sm focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-100"
          :placeholder="placeholder('OpenAI', props.configured.openai)"
          @input="update('openaiKey', $event)"
        />
      </label>
    </div>

    <div v-if="mode === 'gemini'" class="max-w-2xl">
      <label class="block">
        <span class="text-sm font-medium text-slate-700">Gemini API key</span>
        <input
          :value="props.modelValue.geminiKey"
          type="password"
          autocomplete="off"
          class="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 font-mono text-sm text-slate-950 shadow-sm focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-100"
          :placeholder="placeholder('Gemini', props.configured.gemini)"
          @input="update('geminiKey', $event)"
        />
      </label>
    </div>

    <div v-if="mode === 'anthropic'" class="max-w-2xl">
      <label class="block">
        <span class="text-sm font-medium text-slate-700">Anthropic API key</span>
        <input
          :value="props.modelValue.anthropicKey"
          type="password"
          autocomplete="off"
          class="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 font-mono text-sm text-slate-950 shadow-sm focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-100"
          :placeholder="placeholder('Anthropic', props.configured.anthropic)"
          @input="update('anthropicKey', $event)"
        />
      </label>
    </div>
  </section>
</template>
