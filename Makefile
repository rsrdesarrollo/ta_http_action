.PHONY: all clean package install

# App configuration
APP_NAME = ta_http_action
VERSION ?= dev
PACKAGE_NAME = $(APP_NAME)-$(VERSION).tar.gz
BUILD_DIR = build
DIST_DIR = dist

# Files and directories to exclude from the package
EXCLUDE_FILES = .git .gitignore .DS_Store *.pyc __pycache__ build dist Makefile .vscode .idea *.swp *.swo *~

# Default target
all: package

# Build credentials UI
build-ui:
	@echo "Building credentials UI app..."
	@cd front-end/credentials-ui && npm install && npm run build
	@echo "Credentials UI built successfully"

# Create the package
package: clean build-ui
	@echo "Building Splunk package: $(PACKAGE_NAME)"
	@mkdir -p $(BUILD_DIR) $(DIST_DIR)
	@mkdir -p $(BUILD_DIR)/$(APP_NAME)
	
	# Copy app files to build directory
	@echo "Copying files..."
	@cp -r appserver $(BUILD_DIR)/$(APP_NAME)/ 2>/dev/null || true
	@cp -r bin $(BUILD_DIR)/$(APP_NAME)/ 2>/dev/null || true
	@cp -r default $(BUILD_DIR)/$(APP_NAME)/ 2>/dev/null || true
	@cp -r metadata $(BUILD_DIR)/$(APP_NAME)/ 2>/dev/null || true
	@cp -r README $(BUILD_DIR)/$(APP_NAME)/ 2>/dev/null || true
	@cp -r static $(BUILD_DIR)/$(APP_NAME)/ 2>/dev/null || true
	@cp CONTRIBUTORS $(BUILD_DIR)/$(APP_NAME)/ 2>/dev/null || true
	@cp LICENSE $(BUILD_DIR)/$(APP_NAME)/ 2>/dev/null || true
	@cp README.md $(BUILD_DIR)/$(APP_NAME)/ 2>/dev/null || true
	
	# Replace version placeholders
	@echo "Updating version to $(VERSION)..."
	@sed -i.bak 's/__VERSION_PLACEHOLDER__/$(VERSION)/g' $(BUILD_DIR)/$(APP_NAME)/default/app.conf
	@sed -i.bak 's/__VERSION_PLACEHOLDER__/$(VERSION)/g' $(BUILD_DIR)/$(APP_NAME)/appserver/templates/credentials.html
	@rm -f $(BUILD_DIR)/$(APP_NAME)/default/app.conf.bak
	@rm -f $(BUILD_DIR)/$(APP_NAME)/appserver/templates/credentials.html.bak
	
	# Remove excluded files
	@echo "Cleaning up excluded files..."
	@find $(BUILD_DIR)/$(APP_NAME) -name "*.pyc" -delete
	@find $(BUILD_DIR)/$(APP_NAME) -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
	@find $(BUILD_DIR)/$(APP_NAME) -name ".DS_Store" -delete 2>/dev/null || true
	
	# Create the tarball
	@echo "Creating package..."
	@cd $(BUILD_DIR) && tar -czf ../$(DIST_DIR)/$(PACKAGE_NAME) $(APP_NAME)
	@echo "Package created: $(DIST_DIR)/$(PACKAGE_NAME)"

# Clean build artifacts
clean:
	@echo "Cleaning build artifacts..."
	@rm -rf $(BUILD_DIR) $(DIST_DIR)
	@find . -name "*.pyc" -delete 2>/dev/null || true
	@find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
	@echo "Clean complete"

# Install to local Splunk instance (requires SPLUNK_HOME to be set)
install: package
	@if [ -z "$$SPLUNK_HOME" ]; then \
		echo "Error: SPLUNK_HOME environment variable is not set"; \
		exit 1; \
	fi
	@echo "Installing $(APP_NAME) to $$SPLUNK_HOME/etc/apps/"
	@mkdir -p $$SPLUNK_HOME/etc/apps/$(APP_NAME)
	@tar -xzf $(DIST_DIR)/$(PACKAGE_NAME) -C $$SPLUNK_HOME/etc/apps/ --strip-components=1
	@echo "Installation complete. Restart Splunk to load the app."

# Docker commands for local development
docker-up: package
	@echo "Starting Splunk container..."
	@echo "Splunk is starting. Access at http://localhost:8000"
	@echo "Username: splunk, Password: changeme123"
	@docker-compose up

docker-down:
	@echo "Stopping Splunk container..."
	@docker-compose down

docker-restart:
	@echo "Restarting Splunk container..."
	@docker-compose restart splunk

docker-logs:
	@docker-compose logs -f splunk

docker-clean:
	@echo "Stopping and removing Splunk container and volumes..."
	@docker-compose down -v
	@echo "All Docker resources cleaned"

# Show help
help:
	@echo "Splunk App Build System for $(APP_NAME)"
	@echo ""
	@echo "Build targets:"
	@echo "  make build-ui  - Build the credentials UI application"
	@echo "  make package   - Build the Splunk package (.tar.gz)"
	@echo "  make clean    - Remove build artifacts"
	@echo "  make install  - Install to local Splunk (requires SPLUNK_HOME)"
	@echo ""
	@echo "Docker targets:"
	@echo "  make docker-up      - Start Splunk in Docker"
	@echo "  make docker-down    - Stop Splunk Docker container"
	@echo "  make docker-restart - Restart Splunk container"
	@echo "  make docker-logs    - View Splunk logs"
	@echo "  make docker-clean   - Remove container and volumes"
	@echo ""
	@echo "Other:"
	@echo "  make help     - Show this help message"
	@echo ""
	@echo "Current version: $(VERSION)"
