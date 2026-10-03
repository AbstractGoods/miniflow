.PHONY: install uninstall dev run help

CONFIG ?= config/macos/dcommand-applemusic.toml
LABEL = com.abstractgoods.miniflow


help:
	@echo "MiniFlow Commands"
	@echo "  make install     Install CLI tool, copy default config, & register LaunchAgent"
	@echo "                   (Use CONFIG=config/macos/other.toml to install a specific preset)"
	@echo "  make uninstall   Unregister LaunchAgent & remove installed tool"
	@echo "  make dev         Install editable package into local venv using uv"
	@echo "  make run         Run interactively in verbose mode"

install:
	@echo "Installing miniflow CLI via uv..."
	uv tool install --force .
	@echo "Creating configuration directory..."
	mkdir -p $(HOME)/.config/miniflow
	@if [ ! -f $(HOME)/.config/miniflow/config.toml ]; then \
		cp $(CONFIG) $(HOME)/.config/miniflow/config.toml ; \
		echo "Installed config from $(CONFIG) to $(HOME)/.config/miniflow/config.toml" ; \
	fi
	@echo "Setting up LaunchAgent..."
	sed "s|__HOME__|$(HOME)|g" deploy/launchd/$(LABEL).plist.template > $(HOME)/Library/LaunchAgents/$(LABEL).plist
	launchctl unload $(HOME)/Library/LaunchAgents/$(LABEL).plist 2>/dev/null || true
	launchctl load $(HOME)/Library/LaunchAgents/$(LABEL).plist
	@echo "MiniFlow service successfully installed and started!"

uninstall:
	@echo "Stopping LaunchAgent service..."
	launchctl unload $(HOME)/Library/LaunchAgents/$(LABEL).plist 2>/dev/null || true
	rm -f $(HOME)/Library/LaunchAgents/$(LABEL).plist
	@echo "Uninstalling miniflow tool..."
	uv tool uninstall miniflow || true