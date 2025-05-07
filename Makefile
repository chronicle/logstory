# Define the Python build command
build:
	python -m build

# Optional: clean the build directories before building
clean:
	rm -rf dist/ build/

# Optional: clean and build in a single step
rebuild: clean build
