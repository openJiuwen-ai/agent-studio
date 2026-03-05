# HTTPS Configuration Guide

> This document uses the Huawei Cloud environment as an example to guide you through the HTTPS configuration in distributed deployment.

## 1. Solution Overview

In a distributed deployment scenario where the system needs to provide services to the public, it is necessary to configure HTTPS certificates to ensure communication security. At the same time, to protect the system from web attacks, we use Huawei Cloud WAF (Web Application Firewall) for security protection. This solution adopts the following architecture:

- Purchase SSL certificates through Huawei Cloud Certificate Management Service
- Use ELB (Elastic Load Balancing) instead of Nginx
- Configure HTTPS one-way authentication between the browser and ELB
- Use "Cloud Mode - ELB Access" to connect the website to WAF protection

### WAF Access Mode Description

This solution uses the "Cloud Mode - ELB Access" method to connect the website to WAF, which has the following characteristics:

- WAF serves as a bypass detection system and does not directly participate in traffic forwarding, avoiding compatibility and stability issues caused by introducing an additional layer of forwarding
- ELB mirrors traffic to WAF, and WAF synchronizes the detection results to ELB
- ELB decides whether to forward client requests to the origin server based on WAF's detection results

### Request Flow Description

With the "ELB Access WAF Protection" networking solution, the client request flow is as follows:

1. The user enters a domain name in the browser, and the client sends a domain name resolution request to the DNS server
2. The DNS server returns the resolved address corresponding to the domain name (usually the EIP of ELB)
3. The client accesses ELB (Elastic Load Balancer) through the EIP
4. ELB mirrors traffic and forwards it to WAF (Web Application Firewall) for security detection
5. After WAF completes the detection, it synchronizes the detection results to ELB
6. The origin server processes the request and returns a response to ELB
7. ELB forwards normal traffic to the client based on WAF's detection results

### WAF Constraints

When using the "Cloud Mode - ELB Access" method, pay attention to the following constraints:

- Only Huawei Cloud exclusive ELB ("Specification" is "Application-type (HTTP/HTTPS)") is supported
- The following protection rules are not supported: threat intelligence access control, website anti-crawler, web page tampering protection, sensitive information leakage, scanning protection, BOT management, large model detection
- WAF Standard Edition, Professional Edition, or Enterprise Edition must be purchased
- The quotas for domains, QPS, and rule extension packages for Cloud Mode - ELB Access are shared with Cloud Mode - CNAME Access
- Only specific regions are supported. For details, please refer to the official Huawei Cloud documentation

### WAF Access Prerequisites

Before connecting a website to WAF, the following prerequisites must be met:

- WAF Cloud Mode has been purchased
- An exclusive load balancer has been purchased under the same account, and the "Specification" is "Application-type (HTTP/HTTPS)"
- Basic ELB configuration has been completed (listeners, backend server groups, etc.)
- Business traffic has been forwarded normally through ELB

## 2. Configuration Steps

### 1. Purchase an SSL Certificate

Log in to the Huawei Cloud console and purchase an official SSL certificate through the "Certificate Management Service":

- Reference document: [Huawei Cloud SSL Certificate Purchase Guide](https://support.huaweicloud.com/usermanual-ccm/ccm_01_0074.html)

### 2. Configure ELB HTTPS Listener

Configure HTTPS listeners and upload the purchased certificate in the ELB console:

- Reference document: [ELB HTTPS One-way Authentication Configuration](https://support.huaweicloud.com/bestpractice-elb/elb_bp_0800.html)

### 3. Connect the Website to WAF Protection

After completing the ELB configuration, you need to connect the website to WAF for security protection:

1. **Log in to the WAF Console**
   - Access the Huawei Cloud WAF console and log in with your account

2. **Add a Protected Website**
   - In the left navigation bar, click "Website Settings"
   - In the upper left corner of the website list, click "Add Protected Website"
   - Select "Cloud Mode - ELB Access" and click "Start Configuration"

3. **Configure Domain Name Basic Information**
   - **ELB (Load Balancer)**: Select the created exclusive load balancer
   - **ELB Listener**: Select the listener to be protected (supports selecting "All Listeners" or "Specified Listeners")
   - **Website Name**: Customize the website name (optional)
   - **Protected Domain**: Enter the domain name or IP to be protected (public IP/private IP)

4. **Complete Configuration**
   - After confirming that the configuration information is correct, click "Confirm Addition"
   - WAF will automatically associate the selected ELB and its listeners

5. **Verify Access**
   - After configuration is complete, verify that WAF is working properly by accessing the domain name through a browser
   - You can check the protection status on the "Website Settings" page of the WAF console

- Reference document: [Connect a Website to WAF Using Cloud Mode - ELB Access](https://support.huaweicloud.com/usermanual-waf/waf_01_0287.html)

## 3. Notes

- Ensure that the purchased SSL certificate matches the domain name you are using exactly
- The ELB security group configuration needs to open port 443 (HTTPS default port)
- After configuration is complete, verify that HTTPS is working properly by accessing the domain name through a browser