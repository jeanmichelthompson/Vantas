FROM python:3.12.3

# Install dependencies
RUN pip install poetry supabase python-dotenv

# Set working directory
WORKDIR /code

# Copy dependency files
COPY pyproject.toml poetry.lock /code/

# Install project dependencies
RUN poetry install

# Copy project files
COPY . /code/

# Command to run the application
CMD ["python", "main.py"]
