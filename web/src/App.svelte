<script lang="ts">
  import { onMount } from 'svelte';
  import Portfolio from './screens/Portfolio.svelte';
  import Manual from './screens/Manual.svelte';

  let page = window.location.hash.slice(2);

  onMount(() => {
    const updatePage = () => { page = window.location.hash.slice(2); };
    window.addEventListener('hashchange', updatePage);
    return () => window.removeEventListener('hashchange', updatePage);
  });
</script>

{#if page === 'candidates' || page === 'inspector' || page === 'tracked' || page === 'account'}
  <Manual {page} />
{:else}
  <Portfolio />
{/if}
