#!/usr/bin/env zsh

# Currently this script only supports Macs/ZSH, please add more as needed
brew install pre-commit

echo "Installing pre-commit hooks"
pre-commit install
