module.exports = {
  apps: [{
    name: 'espressobot-frontend',
    script: './server-production.js',
    cwd: '/var/www/html/ebot/espressobot/frontend',
    node_args: '-r dotenv/config',
    env: {
      NODE_ENV: 'production'
    }
  }]
};