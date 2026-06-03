FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir sqlalchemy==2.0.36

# Copy application code
COPY streamlit_app/ ./streamlit_app/
COPY src/ ./src/
COPY assests/ ./assests/

# Expose Streamlit port
EXPOSE 8501

# Health check
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health || exit 1

# Run Streamlit
CMD ["streamlit", "run", "streamlit_app/app.py", \
     "--server.port=8501", \
     "--server.address=0.0.0.0", \
     "--server.headless=true", \
     "--theme.base=dark", \
     "--theme.primaryColor=#6366f1", \
     "--theme.backgroundColor=#0f172a", \
     "--theme.secondaryBackgroundColor=#1e293b", \
     "--theme.textColor=#e2e8f0"]
