#!/bin/bash

SERVICE_DIR="/usr/lib/euler-copilot-framework/mcp_center/service"

for service_file in "$SERVICE_DIR"/*.service; do
    if [ -f "$service_file" ]; then
        service_name=$(basename "$service_file" .service)
        systemctl enable "$service_name"
        systemctl start "$service_name"
    fi
done

#systrace
#echo "[systrace]
#name=systrace
#baseurl=https://eulermaker.compass-ci.openeuler.openatom.cn/api/ems4/repositories/openEuler-24.03-LTS-SP2:epol/openEuler%3A24.03-LTS-SP2/x86_64/
#enabled=1
#gpgcheck=0
#sslverify=0
#gpgkey=http://repo.openeuler.org/openEuler-24.03-LTS-SP2/OS//RPM-GPG-KEY-openEuler">>/etc/yum.repos.d/systrace.repo

dnf install sysTrace-failslow sysTrace-mcpserver -y
systemctl enable systrace-mcpserver
systemctl start systrace-mcpserver

#euler-copilot-tune
#echo "[tune]
#name=tune
#baseurl=https://eulermaker.compass-ci.openeuler.openatom.cn/api/ems4/repositories/houxu:openEuler-24.03-LTS-SP2:epol/openEuler%3A24.03-LTS-SP2/x86_64/
#enabled=1
#gpgcheck=0
#sslverify=0
#gpgkey=http://repo.openeuler.org/openEuler-24.03-LTS-SP2/OS//RPM-GPG-KEY-openEuler">>/etc/yum.repos.d/tune.repo

dnf install euler-copilot-tune -y
systemctl enable tune-mcpserver
systemctl start tune-mcpserver



