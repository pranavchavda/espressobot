import express from 'express';

console.log('Testing basic express...');
const app = express();
app.get('/test', (req, res) => res.json({ ok: true }));
console.log('Basic express works');

try {
  console.log('Testing dotenv...');
  const dotenv = await import('dotenv');
  dotenv.config();
  console.log('dotenv works');
  
  console.log('Testing cors...');
  const cors = await import('cors');
  console.log('cors works');
  
  console.log('Testing passport...');
  const passport = await import('passport');
  console.log('passport works');
  
  console.log('Testing body-parser...');
  const bodyParser = await import('body-parser');
  console.log('body-parser works');
  
  console.log('All basic imports work. Trying server imports one by one...');
  
  console.log('Testing auth.js...');
  const auth = await import('./server/auth.js');
  console.log('auth.js works');
  
} catch (error) {
  console.error('Error during import:', error);
  process.exit(1);
}

console.log('All imports successful');
process.exit(0);