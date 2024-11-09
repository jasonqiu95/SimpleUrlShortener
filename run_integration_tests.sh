#!/bin/bash

set -e


# Wait for the app to be ready
echo "Waiting for the app to start..."
until $(curl --output /dev/null --silent --head --fail --max-time 2 http://localhost:5000/health); do
    printf '.'
    sleep 2
done
echo "App is up!"

# Test the shortening functionality
echo "Testing URL shortening..."
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}' http://localhost:5000/shorten)

echo $RESPONSE
echo $DATABASE_URL
echo $REDIS_URL
# Use awk to split the response into body and status code
BODY=$(echo "$RESPONSE" | awk 'NR==1{body=$0; next} {status=$0} END{print body}')
STATUS_CODE=$(echo "$RESPONSE" | awk 'NR==1{body=$0; next} {status=$0} END{print status}')
SHORT_URL=$(echo $BODY | jq -r '.short_url')

# Validate status code and response body
if [ "$STATUS_CODE" -ne 200 ]; then
  echo "App responded with unexpected HTTP status: $STATUS_CODE"
  exit 1
fi

if [ -z "$SHORT_URL" ] || [ "$SHORT_URL" == "null" ]; then
  echo "URL shortening test failed: Invalid or missing short_url in response body."
  exit 1
fi
echo "Short URL generated: $SHORT_URL"

# Capture both the redirect URL and status code
REDIRECT_RESPONSE=$(curl -s -o /dev/null -w "%{http_code} %{redirect_url}" http://localhost:5000/$SHORT_URL)

# Extract status code and redirect URL from the response
REDIRECT_STATUS_CODE=$(echo "$REDIRECT_RESPONSE" | awk '{print $1}')
REDIRECT_URL=$(echo "$REDIRECT_RESPONSE" | awk '{print $2}')

# Validate the status code
if [ "$REDIRECT_STATUS_CODE" -ne 302 ]; then
  echo "Redirection test failed: Expected HTTP status 302 but got $REDIRECT_STATUS_CODE"
  exit 1
fi

# Validate the redirect URL
if [ "$REDIRECT_URL" != "https://example.com/" ]; then
  echo "Redirection test failed: Expected https://example.com/ but got $REDIRECT_URL"
  exit 1
fi
echo "Redirection test passed!"

echo "Integration tests completed successfully!"