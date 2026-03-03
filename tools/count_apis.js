const https = require('https');
const data = JSON.stringify({ scope: { type: 'ALL' } });
const opt = {
  hostname: 'apifox.dragonpass.com.cn',
  port: 443,
  path: '/v1/projects/345747/export-openapi',
  method: 'POST',
  headers: {
    'Authorization': 'Bearer APS-J75tJzWEexmcQd5SESOh52D4iw0oFVA6',
    'X-Apifox-Version': '2024-03-28',
    'Content-Type': 'application/json',
    'Content-Length': Buffer.byteLength(data)
  }
};

const r = https.request(opt, res => {
  let d = '';
  res.on('data', c => d += c);
  res.on('end', () => {
    const spec = JSON.parse(d);
    const paths = Object.keys(spec.paths || {});
    let total = 0;
    const list = [];
    paths.forEach(p => {
      const methods = Object.keys(spec.paths[p]).filter(m =>
        ['get', 'post', 'put', 'delete', 'patch', 'head', 'options'].includes(m)
      );
      total += methods.length;
      methods.forEach(m => {
        const ep = spec.paths[p][m];
        list.push(`  ${m.toUpperCase().padEnd(7)} ${p}  - ${ep.summary || 'No description'}`);
      });
    });
    console.log('=== API Stats ===');
    console.log('OpenAPI Version:', spec.openapi);
    console.log('Project Title:', spec.info?.title);
    console.log('Path Count:', paths.length);
    console.log('Endpoint Count:', total);
    console.log('\n=== Endpoint List ===');
    list.forEach(l => console.log(l));
  });
});
r.on('error', e => console.error(e));
r.write(data);
r.end();
