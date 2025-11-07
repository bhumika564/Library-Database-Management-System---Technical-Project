# Start with a lightweight, official Python base image
FROM python:3.9-slim

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements file *first* to leverage Docker cache
COPY requirements.txt .

# Install the Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Now, copy the rest of your application code into the container
COPY . .

# Tell Docker that your app will listen on port 5000
EXPOSE 5000

# Set the command to run your app using Gunicorn
# This runs your 'app.py' file, looking for the 'app' variable
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]