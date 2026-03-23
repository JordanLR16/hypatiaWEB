FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

WORKDIR /workspace

# System packages required by Hypatia's Python tooling and ns-3 build/test flow.
RUN apt-get update && apt-get install -y --no-install-recommends \
    bash \
    build-essential \
    ca-certificates \
    git \
    gnuplot \
    lcov \
    libgeos-dev \
    libopenmpi-dev \
    libproj-dev \
    openmpi-bin \
    openmpi-common \
    proj-bin \
    proj-data \
    python-is-python3 \
    python3 \
    python3-pip \
    unzip \
    && rm -rf /var/lib/apt/lists/*

COPY hypatia_build.sh /workspace/
COPY ns3-sat-sim /workspace/ns3-sat-sim
COPY satgenpy /workspace/satgenpy
COPY satviz /workspace/satviz
COPY integration_tests /workspace/integration_tests
COPY README.md /workspace/
COPY LICENSE /workspace/

# Normalize shell scripts copied from Windows so bash can execute them in Linux.
RUN find /workspace -type f -name "*.sh" -exec sed -i 's/\r$//' {} +

# Install Python dependencies listed by the project setup scripts.
RUN python3 -m pip install --no-cache-dir --upgrade pip && \
    python3 -m pip install --no-cache-dir \
    numpy \
    astropy \
    ephem \
    networkx \
    sgp4 \
    geopy \
    matplotlib \
    statsmodels \
    cartopy \
    fastapi \
    pydantic \
    uvicorn && \
    python3 -m pip install --no-cache-dir \
    git+https://github.com/snkas/exputilpy.git@v1.6 \
    git+https://github.com/snkas/networkload.git@v1.3

# Populate the basic-sim dependency when the local checkout does not include
# initialized submodule contents.
RUN if [ ! -f /workspace/ns3-sat-sim/simulator/contrib/basic-sim/wscript ]; then \
      rm -rf /workspace/ns3-sat-sim/simulator/contrib/basic-sim && \
      git clone https://github.com/snkas/basic-sim /workspace/ns3-sat-sim/simulator/contrib/basic-sim && \
      git -C /workspace/ns3-sat-sim/simulator/contrib/basic-sim checkout 3b32597c183e1039be7f0bede17d36d354696776; \
    fi

# Patch an older basic-sim source pattern that newer GCC versions reject when
# warnings are treated as errors.
RUN sed -i 's/const std::pair<std::string, std::string>& key_val/const std::pair<const std::string, std::string>\& key_val/' \
    /workspace/ns3-sat-sim/simulator/contrib/basic-sim/model/core/basic-simulation.cc

# Build the ns-3 component during image creation so the container is ready to use.
RUN bash hypatia_build.sh

CMD ["/bin/bash"]
