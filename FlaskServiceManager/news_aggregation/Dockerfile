# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container
COPY . .

# Set environment variables
ENV BASE_URL="https://newsdata.io/api/1/latest"
ENV API_KEY="pub_4797424ba30726a8d823c8e203845387fe464"
ENV GOOGLE_API_KEY="AIzaSyBDcq_pW15jmoPhF4rLDShj2Ikq5OtP-eE"
# Make port 8002 available to the world outside this container
EXPOSE 80

# Run the Flask app
CMD ["python", "app.py", "--host=0.0.0.0", "--port=80"]
