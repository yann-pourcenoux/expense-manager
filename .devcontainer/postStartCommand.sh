# Add .local/bin to PATH needed to find the packages
export PATH=$PATH:/home/vscode/.local/bin


# Update pip
pip install --upgrade pip
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install
