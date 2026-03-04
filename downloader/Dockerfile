FROM continuumio/miniconda3:25.3.1-1

ENV DEBIAN_FRONTEND=noninteractive

# System dependencies still needed for kernel-level networking protocols like OpenVPN
RUN apt-get update && apt-get install -y \
    openvpn \
    iproute2 \
    iptables \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY environment.yml .

# Create the Conda environment (this installs aria2, python, and pip deps)
RUN conda env create -f environment.yml

COPY . .

# Install the downloader package into the Conda environment
RUN conda run --no-capture-output -n pfirsichfest-downloader pip install --no-deps .

ENTRYPOINT ["conda", "run", "--no-capture-output", "-n", "pfirsichfest-downloader"]
CMD ["python", "-m", "downloader.controller"]
