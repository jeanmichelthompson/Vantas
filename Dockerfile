# Use the official Python image.
# https://hub.docker.com/_/python
FROM python:3.12.3

# Set the working directory to /code.
WORKDIR /code

# Copy the requirements.txt file into the container.
COPY requirements.txt /code/

# Install any dependencies specified in requirements.txt.
RUN pip install --no-cache-dir -r requirements.txt

# Copy the current directory contents into the container at /code.
COPY . /code/

# Make port 80 available to the world outside this container.
EXPOSE 80

# Run app.py when the container launches.
CMD ["python", "main.py"]
