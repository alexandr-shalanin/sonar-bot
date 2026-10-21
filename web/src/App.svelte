<script lang="ts">
  const stage: string = 'Foundation ready';
</script>

<main>
  <h1>Sonar</h1>
  <p>{stage}</p>
  <p>Discovery and trading are not connected yet.</p>
</main>

<style>
  :global(body) {
    margin: 0;
    font-family: system-ui, sans-serif;
    background: #101820;
    color: #f5f7fa;
  }

  main {
    max-width: 38rem;
    margin: 15vh auto;
    padding: 2rem;
  }
</style>
