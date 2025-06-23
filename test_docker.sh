#!/bin/bash
# Test script for Paper2Poster Docker setup

echo "============================================="
echo "Testing Paper2Poster Docker Setup"
echo "============================================="

# Function to check if service is ready
wait_for_service() {
    local max_attempts=30
    local attempt=1
    
    echo "Waiting for service to be ready..."
    while [ $attempt -le $max_attempts ]; do
        if curl -s http://localhost:6025/health > /dev/null; then
            echo "✅ Service is ready!"
            return 0
        fi
        echo "Attempt $attempt/$max_attempts: Service not ready yet..."
        sleep 10
        attempt=$((attempt + 1))
    done
    
    echo "❌ Service failed to start after $max_attempts attempts"
    return 1
}

# 1. Build the Docker image
echo ""
echo "1. Building Docker image..."
docker-compose build

# 2. Start the service
echo ""
echo "2. Starting the service..."
docker-compose up -d

# 3. Check if container is running
echo ""
echo "3. Checking container status..."
docker-compose ps

# 4. Follow logs for a bit to see model download progress
echo ""
echo "4. Monitoring startup logs (press Ctrl+C to continue)..."
timeout 30s docker-compose logs -f paper2poster || true

# 5. Wait for service to be ready
echo ""
echo "5. Waiting for service to be ready..."
if wait_for_service; then
    # 6. Test health endpoint
    echo ""
    echo "6. Testing health endpoint..."
    curl -s http://localhost:6025/health | jq .
    
    # 7. Show API documentation URL
    echo ""
    echo "7. API Documentation available at:"
    echo "   - Interactive docs: http://localhost:6025/docs"
    echo "   - ReDoc: http://localhost:6025/redoc"
    
    echo ""
    echo "============================================="
    echo "✅ Docker setup test completed successfully!"
    echo "============================================="
    echo ""
    echo "You can now:"
    echo "1. Upload PDFs using the API at http://localhost:6025/docs"
    echo "2. Run: python test_api.py --pdf your_paper.pdf"
    echo "3. Monitor logs: docker-compose logs -f paper2poster"
else
    echo ""
    echo "============================================="
    echo "❌ Docker setup test failed!"
    echo "============================================="
    echo ""
    echo "Check the logs for errors:"
    echo "docker-compose logs paper2poster"
    exit 1
fi 