#!/bin/bash
# Deploy 13F Tracker using Docker

set -e

echo "🐋 Hedge Fund 13F Tracker - Deployment Script"
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not found. Please install Docker first."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose not found. Please install Docker Compose first."
    exit 1
fi

# Parse arguments
MODE=${1:-web}

# Check environment variables
if [ "$MODE" = "bot" ] && [ -z "$TELEGRAM_BOT_TOKEN" ]; then
    echo "⚠️  TELEGRAM_BOT_TOKEN not set. Bot will not start properly."
    echo "Set it with: export TELEGRAM_BOT_TOKEN=your_token"
fi

echo "📦 Building and starting services..."
echo "Mode: $MODE"
echo ""

case $MODE in
    web)
        docker-compose up -d tracker-web
        echo ""
        echo "✅ Web dashboard started!"
        echo "📊 Dashboard: http://localhost:8000"
        echo "📡 API: http://localhost:8000/api/funds"
        ;;
    bot)
        docker-compose --profile bot up -d tracker-bot
        echo ""
        echo "✅ Telegram bot started!"
        echo "🤖 Bot is now polling for messages"
        ;;
    reporter)
        if [ -z "$REPORT_EMAIL" ]; then
            echo "⚠️  REPORT_EMAIL not set. Please set it first."
            exit 1
        fi
        docker-compose --profile reporter up -d tracker-reporter
        echo ""
        echo "✅ Daily email reporter started!"
        echo "📧 Reports will be sent to: $REPORT_EMAIL"
        ;;
    all)
        docker-compose --profile bot --profile reporter up -d
        echo ""
        echo "✅ All services started!"
        echo "📊 Dashboard: http://localhost:8000"
        echo "🤖 Bot: Running"
        echo "📧 Reporter: Running"
        ;;
    stop)
        docker-compose down
        echo ""
        echo "✅ All services stopped"
        ;;
    logs)
        docker-compose logs -f
        ;;
    *)
        echo "Usage: $0 [web|bot|reporter|all|stop|logs]"
        echo ""
        echo "Modes:"
        echo "  web       - Start web dashboard only (default)"
        echo "  bot       - Start Telegram bot"
        echo "  reporter  - Start daily email reporter"
        echo "  all       - Start all services"
        echo "  stop      - Stop all services"
        echo "  logs      - View logs"
        echo ""
        echo "Environment variables:"
        echo "  TELEGRAM_BOT_TOKEN - Required for bot mode"
        echo "  REPORT_EMAIL       - Required for reporter mode"
        echo "  RESEND_API_KEY     - Required for email reports"
        exit 1
        ;;
esac

echo ""
echo "Useful commands:"
echo "  View logs:  docker-compose logs -f"
echo "  Stop:       ./deploy.sh stop"
echo "  Status:     docker-compose ps"
