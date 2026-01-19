#!/bin/bash

REGISTRY="ghcr.io/kdw8219"

echo "Building commerce_management..."
docker build -t $REGISTRY/commerce_management:latest ../commerce_management