<script lang="ts">
  import { cn } from "$lib/utils";

  interface Props {
    value?: string;
    type?: string;
    placeholder?: string;
    disabled?: boolean;
    autocomplete?: string;
    autofocus?: boolean;
    id?: string;
    name?: string;
    required?: boolean;
    class?: string;
    oninput?: (e: Event & { currentTarget: HTMLInputElement }) => void;
    onkeydown?: (e: KeyboardEvent) => void;
  }

  let {
    value = $bindable(""),
    type = "text",
    placeholder,
    disabled = false,
    autocomplete,
    autofocus = false,
    id,
    name,
    required = false,
    class: cls = "",
    oninput,
    onkeydown,
  }: Props = $props();
</script>

<input
  {id}
  {name}
  {type}
  {placeholder}
  {disabled}
  {autocomplete}
  {required}
  bind:value
  {oninput}
  {onkeydown}
  {autofocus}
  class={cn(
    "flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm",
    "placeholder:text-muted-foreground",
    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
    "disabled:cursor-not-allowed disabled:opacity-50",
    cls,
  )}
/>
