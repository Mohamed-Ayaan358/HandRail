import test from 'node:test';
import assert from 'node:assert/strict';
import { extract } from '../extract.mjs';
test('masks names without changing naturally named controls',()=>{
 const rows=extract('<button aria-label="Close" class="lucide-x"></button><button>Save</button><img alt="Dog" src="/dog.png">','https://example.org');
 assert.equal(rows.length,2);assert.equal(rows[0].reference,'Close');assert.ok(!rows[0].input.html.includes('aria-label'));assert.ok(!rows[1].input.html.includes('alt='));
});
test('skips hidden, inert, title fallback and associated label controls',()=>{
 const rows=extract('<div hidden><button aria-label="A"></button></div><div inert><button aria-label="B"></button></div><button aria-label="C" title="C"></button><label for="x">Name</label><input id="x" aria-label="Name">','https://example.org');
 assert.equal(rows.length,0);
});
test('masks descendant and referenced names, strips scripts, handlers and URL queries',()=>{
 const rows=extract('<button onclick="evil()"><svg aria-label="Search"></svg><script>SECRET</script></button><span id="lbl">Next</span><a href="/next?token=SECRET#x" aria-labelledby="lbl"></a>','https://example.org');
 assert.equal(rows.length,2);assert.ok(rows.every(r=>!r.input.html.includes('SECRET')&&!r.input.html.includes('aria-label')));
});
test('deduplicates identical controls and restores names for later computation',()=>{
 const rows=extract('<button class="x" aria-label="Close"></button><button class="x" aria-label="Close"></button>','https://example.org');
 assert.equal(rows.length,1);
});
