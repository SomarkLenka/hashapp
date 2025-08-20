# Simple Dockerfile that uses pre-built base with all dependencies
ARG BASE_IMAGE=somark28/myapp-base:latest
FROM ${BASE_IMAGE}

# Switch to root to copy files
USER root

# Copy application files with proper ownership
COPY --chown=appuser:appuser hash_generator_throttled.py config.json credentials.json ./
# Rename to hash_generator.py for compatibility
RUN mv hash_generator_throttled.py hash_generator.py

# Copy verification scripts
COPY --chown=appuser:appuser verify_hashgen.sh verify_inside_container.py ./
RUN chmod +x verify_hashgen.sh

# Switch back to non-root user
USER appuser

# App-specific environment variables  
ENV CONFIG_PATH=/app/config.json \
    GOOGLE_APPLICATION_CREDENTIALS=/app/credentials.json

# Health check - verify the process is running
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD pgrep -f hash_generator.py || exit 1

# Run the application
CMD ["python", "hash_generator.py"]