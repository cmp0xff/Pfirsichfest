FROM continuumio/miniconda3:latest

ENV PYTHONUNBUFFERED=1

WORKDIR /app
COPY environment.yml .

# Create the Conda environment
RUN conda env create -f environment.yml

COPY . .

# Run the web service on container startup through Conda
ENTRYPOINT ["conda", "run", "--no-capture-output", "-n", "pfirsichfest-bot"]
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
