const { spawn } = require('child_process');
const http = require('http');

let mintlifyProcess;
let isReady = false;

// Start Mintlify dev server
function startMintlify() {
  if (mintlifyProcess) return;
  
  mintlifyProcess = spawn('npx', ['mintlify', 'dev', '--port', '3000'], {
    cwd: process.cwd(),
    env: { ...process.env, PORT: '3000' }
  });

  mintlifyProcess.stdout.on('data', (data) => {
    console.log(`Mintlify: ${data}`);
    if (data.toString().includes('Local Mintlify instance is ready')) {
      isReady = true;
    }
  });

  mintlifyProcess.stderr.on('data', (data) => {
    console.error(`Mintlify Error: ${data}`);
  });

  mintlifyProcess.on('close', (code) => {
    console.log(`Mintlify process exited with code ${code}`);
    mintlifyProcess = null;
    isReady = false;
  });
}

module.exports = async (req, res) => {
  // Start Mintlify if not already running
  if (!mintlifyProcess) {
    startMintlify();
    
    // Wait for Mintlify to be ready (max 30 seconds)
    let waitTime = 0;
    while (!isReady && waitTime < 30000) {
      await new Promise(resolve => setTimeout(resolve, 100));
      waitTime += 100;
    }
  }

  if (!isReady) {
    return res.status(503).send('Documentation server is starting up, please refresh in a few seconds...');
  }

  // Proxy the request to Mintlify dev server
  const options = {
    hostname: 'localhost',
    port: 3000,
    path: req.url,
    method: req.method,
    headers: req.headers
  };

  const proxy = http.request(options, (proxyRes) => {
    res.writeHead(proxyRes.statusCode, proxyRes.headers);
    proxyRes.pipe(res, { end: true });
  });

  proxy.on('error', (err) => {
    console.error('Proxy error:', err);
    res.status(502).send('Error connecting to documentation server');
  });

  req.pipe(proxy, { end: true });
}; 