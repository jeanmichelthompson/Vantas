FROM python:3.12.3
RUN pip install poetry
RUN pip install supabase
RUN pip install python-dotenv
WORKDIR /code
COPY pyproject.toml poetry.lock /code/
RUN poetry config virtualenvs.create false && poetry install --no-interaction --no-ansi
COPY . /code
CMD python main.py