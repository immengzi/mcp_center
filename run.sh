#!/bin/bash

SERVICE_DIR="/usr/lib/euler-copilot-framework/mcp_center/service"

for service_file in "$SERVICE_DIR"/*.service; do
    if [ -f "$service_file" ]; then
        service_name=$(basename "$service_file" .service)
        systemctl enable "$service_name"
        systemctl start "$service_name"
    fi
done
