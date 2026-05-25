#!/bin/bash
# Start FinBot scheduler in background

cd /root/.openclaw/workspace/finbot

# Create logs directory if needed
mkdir -p logs

# Kill any existing bot processes
pkill -f "python3 src/main.py" 2>/dev/null

# Start the bot
nohup python3 src/main.py > logs/bot.log 2>&1 &

echo "FinBot started with PID: $!"
echo "Logs: /root/.openclaw/workspace/finbot/logs/bot.log"
echo ""
echo "Schedule:"
echo "  - Daily digest: 09:00"
echo "  - Market summary: 09:00, 16:00"
echo "  - Breaking news: every 6 hours"
echo "  - Weekly roundup: Sunday 18:00"
echo ""
echo "To stop: pkill -f 'python3 src/main.py'"
echo "To check status: tail -f logs/bot.log"