FROM continuumio/miniconda3:25.3.1-1

ENV PYTHONUNBUFFERED=1

WORKDIR /app
COPY environment.yml .

# Create the Conda environment
RUN conda env create -f environment.yml

COPY . .

# Install the bot package into the Conda environment
RUN conda run --no-capture-output -n pfirsichfest-bot pip install --no-deps .

# Run the web service on container startup through Conda
ENTRYPOINT ["conda", "run", "--no-capture-output", "-n", "pfirsichfest-bot"]
CMD ["uvicorn", "bot.main:app", "--host", "0.0.0.0", "--port", "8080"]
