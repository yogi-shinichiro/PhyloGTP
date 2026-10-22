FROM mambaorg/micromamba:2.9.0
COPY --chown=$MAMBA_USER:$MAMBA_USER environment.yml /tmp/environment.yml
RUN micromamba install --yes --name base --file /tmp/environment.yml && micromamba clean --all --yes
ARG MAMBA_DOCKERFILE_ACTIVATE=1
WORKDIR /app
COPY --chown=$MAMBA_USER:$MAMBA_USER requirements.txt /app/requirements.txt
RUN python -m pip install --no-cache-dir -r /app/requirements.txt
COPY --chown=$MAMBA_USER:$MAMBA_USER *.py /app/
RUN python -m compileall -q /app
RUN mkdir -p /home/mambauser/data
ENV PATH=/opt/conda/bin:$PATH \
    PYTHONUNBUFFERED=1 MPLBACKEND=Agg PYTHONPATH=/app \
    PHYLOGPT_DATA_DIR=/home/mambauser/data \
    PHYLOGPT_TOOL_PATH=/opt/conda/bin:/usr/local/bin:/usr/bin:/bin \
    OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
WORKDIR /home/mambauser/data
EXPOSE 8501
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD ["/opt/conda/bin/python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8501/_stcore/health', timeout=3)"]
CMD ["python", "/app/container_start.py"]
