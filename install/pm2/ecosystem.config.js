module.exports = {
  apps: [{
    name: 'terminalbot',
    script: 'uv',
    args: 'run terminalbot',

    // Restart behavior
    autorestart: true,
    max_restarts: 10,          // Limit restarts in short time window
    min_uptime: '10s',         // Must run 10s to count as successful start
    restart_delay: 5000,       // Wait 5s before restarting
    // Note: PM2 will auto-restart on all exits (including /shutdown). Use 'pm2 stop terminalbot' to prevent.

    // Resource limits
    max_memory_restart: '500M', // Restart if memory exceeds 500MB

    // Logging
    error_file: './logs/error.log',
    out_file: './logs/output.log',
    log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
    merge_logs: true,

    // Environment
    env: {
      NODE_ENV: 'production',
    },

    // Other
    watch: false,              // Don't watch for file changes
    ignore_watch: ['logs', '.git', 'openspec'],
  }]
}
