FROM python:3.12-slim

# Install git
RUN apt-get update -y
RUN apt-get install -y git

# Add a non root user
RUN adduser vscode
