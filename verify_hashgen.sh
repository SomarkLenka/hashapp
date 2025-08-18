#!/bin/bash

echo "========================================="
echo "HashGen Container Verification Script"
echo "========================================="
echo ""

# Check if container is running
echo "1. Checking running containers..."
echo "---------------------------------"
docker ps | grep -E "hashgen|myapp" || echo "No hashgen container found running"
echo ""

# Get container name or ID
CONTAINER=$(docker ps --format "{{.Names}}" | grep -E "hashgen|myapp" | head -1)
if [ -z "$CONTAINER" ]; then
    CONTAINER=$(docker ps --format "{{.ID}}" | head -1)
fi

if [ -z "$CONTAINER" ]; then
    echo "ERROR: No running container found"
    echo "Start the container with: docker run -d --name hashgen somark28/hashgen:latest"
    exit 1
fi

echo "Using container: $CONTAINER"
echo ""

# Check container health
echo "2. Container Status..."
echo "----------------------"
docker inspect $CONTAINER --format='{{.State.Status}}' | xargs echo "Status:"
docker inspect $CONTAINER --format='{{.State.Health.Status}}' 2>/dev/null | xargs echo "Health:"
docker inspect $CONTAINER --format='{{.State.StartedAt}}' | xargs echo "Started:"
echo ""

# Check CPU/Memory usage
echo "3. Resource Usage..."
echo "--------------------"
docker stats $CONTAINER --no-stream --format "table {{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}"
echo ""

# Check recent logs
echo "4. Recent Logs (last 20 lines)..."
echo "----------------------------------"
docker logs $CONTAINER --tail 20 2>&1 | grep -E "(INFO|ERROR|WARNING)" || echo "No recent logs"
echo ""

# Check for errors
echo "5. Error Check..."
echo "-----------------"
ERROR_COUNT=$(docker logs $CONTAINER 2>&1 | grep -c "ERROR" || echo "0")
echo "Total errors in logs: $ERROR_COUNT"

if [ "$ERROR_COUNT" -gt "0" ]; then
    echo "Last 5 errors:"
    docker logs $CONTAINER 2>&1 | grep "ERROR" | tail -5
fi
echo ""

# Check BigTable operations
echo "6. BigTable Upload Status..."
echo "-----------------------------"
UPLOAD_COUNT=$(docker logs $CONTAINER 2>&1 | grep -c "Uploaded.*hashes to BigTable" || echo "0")
echo "Successful uploads: $UPLOAD_COUNT"

if [ "$UPLOAD_COUNT" -gt "0" ]; then
    echo "Last upload:"
    docker logs $CONTAINER 2>&1 | grep "Uploaded.*hashes to BigTable" | tail -1
else
    echo "No uploads yet (uploads occur every 10 minutes or after 10M hashes)"
fi
echo ""

# Check hashrate
echo "7. Hashrate Performance..."
echo "---------------------------"
LAST_HASHRATE=$(docker logs $CONTAINER 2>&1 | grep "Hashrate:" | tail -1)
if [ -n "$LAST_HASHRATE" ]; then
    echo "$LAST_HASHRATE"
else
    echo "No hashrate data yet (reported with uploads)"
fi
echo ""

# Check monitoring server connection
echo "8. Monitoring Server Status..."
echo "-------------------------------"
MONITOR_ERRORS=$(docker logs $CONTAINER 2>&1 | grep -c "Failed to report hashrate" || echo "0")
echo "Monitoring failures: $MONITOR_ERRORS"

if [ "$MONITOR_ERRORS" -gt "0" ]; then
    echo "Last monitoring error:"
    docker logs $CONTAINER 2>&1 | grep "Failed to report hashrate" | tail -1
fi
echo ""

# Process check
echo "9. Python Process Check..."
echo "---------------------------"
docker exec $CONTAINER ps aux | grep python | head -1 || echo "Python process not found!"
echo ""

# Summary
echo "========================================="
echo "SUMMARY"
echo "========================================="

if docker exec $CONTAINER ps aux | grep -q python; then
    echo "✓ Container is running"
    echo "✓ Python process is active"
    
    if [ "$UPLOAD_COUNT" -gt "0" ]; then
        echo "✓ BigTable uploads working"
    else
        echo "⚠ No BigTable uploads yet (may be normal if < 10 min runtime)"
    fi
    
    if [ "$MONITOR_ERRORS" -eq "0" ]; then
        echo "✓ Monitoring server connected"
    else
        echo "⚠ Some monitoring failures detected"
    fi
    
    if [ "$ERROR_COUNT" -eq "0" ]; then
        echo "✓ No errors in logs"
    else
        echo "⚠ Found $ERROR_COUNT errors in logs"
    fi
else
    echo "✗ Container may not be working properly"
fi

echo ""
echo "For real-time logs: docker logs -f $CONTAINER"
echo "For shell access: docker exec -it $CONTAINER bash"