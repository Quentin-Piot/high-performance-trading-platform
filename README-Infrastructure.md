# High-Performance Trading Platform - Infrastructure Setup

This document provides a complete guide for setting up the infrastructure for the High-Performance Trading Platform using Docker and Terraform on AWS.

## 🏗️ Architecture Overview

The application is deployed as a containerized solution on a single AWS EC2 t2.micro instance with the following components:

- **Frontend**: Vue.js + Vite application served by Nginx
- **Backend**: FastAPI application running with Uvicorn
- **Database**: PostgreSQL 16
- **Reverse Proxy**: Nginx (routes `/api` requests to backend)

## 📁 Infrastructure Files

### Docker Configuration

1. **`web/Dockerfile`** - Multi-stage build for Vue.js frontend with Nginx
2. **`web/nginx.conf`** - Nginx configuration for static files and API proxy
3. **`backend/api/Dockerfile.new`** - FastAPI backend with Uvicorn
4. **`docker-compose.yml`** - Orchestrates all services

### Terraform Configuration

1. **`terraform/main.tf`** - Complete AWS infrastructure setup
2. **`terraform/terraform.tfvars.example`** - Example variables file

### Deployment Scripts

1. **`deploy.sh`** - Automated deployment script

## 🚀 Quick Start

### Prerequisites

- AWS CLI configured with appropriate credentials
- Terraform installed (>= 1.0)
- Docker and Docker Compose installed locally (for testing)
- An AWS Key Pair for EC2 access

### Step 1: Configure Terraform Variables

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars` with your values:
```hcl
aws_region = "us-east-1"
instance_type = "t2.micro"
key_name = "your-aws-key-pair-name"
allowed_ssh_cidr = "YOUR_IP/32"  # Replace with your IP for security
```

### Step 2: Deploy Infrastructure

```bash
# Initialize Terraform
terraform init

# Plan the deployment
terraform plan

# Apply the infrastructure
terraform apply
```

### Step 3: Deploy Application

```bash
# Return to project root
cd ..

# Run the deployment script
./deploy.sh
```

The script will:
- Package your application
- Copy files to the EC2 instance
- Build and start Docker containers
- Verify deployment

### Step 4: Access Your Application

After successful deployment, your application will be available at:
```
http://YOUR_INSTANCE_PUBLIC_IP
```

## 🔧 Manual Deployment (Alternative)

If you prefer manual deployment:

### 1. Connect to EC2 Instance

```bash
ssh -i your-key.pem ec2-user@YOUR_INSTANCE_IP
```

### 2. Clone/Copy Your Code

```bash
# Option 1: Clone from repository
git clone https://github.com/your-username/your-repo.git
cd your-repo

# Option 2: Copy files using SCP (from local machine)
scp -i your-key.pem -r . ec2-user@YOUR_INSTANCE_IP:/home/ec2-user/app/
```

### 3. Build and Start Services

```bash
sudo docker-compose up -d --build
```

## 📊 Service Configuration

### Frontend Service
- **Port**: 80 (mapped to host)
- **Build Context**: `./web`
- **Nginx Config**: Serves static files and proxies `/api` to backend

### Backend Service
- **Port**: 8000 (internal only)
- **Build Context**: `./backend/api`
- **Environment Variables**:
  - `DATABASE_URL`: PostgreSQL connection string
  - `JWT_SECRET`: JWT signing secret
  - `ENV`: Environment setting

### Database Service
- **Image**: PostgreSQL 16
- **Port**: 5432 (internal only)
- **Volume**: `postgres_data` for persistence
- **Health Check**: Ensures database is ready before starting backend

## 🔒 Security Configuration

### Security Group Rules
- **SSH (22)**: Configurable CIDR (default: your IP)
- **HTTP (80)**: Open to internet (0.0.0.0/0)
- **HTTPS (443)**: Open to internet (0.0.0.0/0)
- **Backend/DB ports**: Not exposed to internet

### Best Practices
1. **Change default passwords**: Update PostgreSQL and JWT secrets
2. **Restrict SSH access**: Use your specific IP instead of 0.0.0.0/0
3. **Enable HTTPS**: Consider adding SSL certificates for production
4. **Regular updates**: Keep AMI and packages updated

## 🛠️ Maintenance Commands

### View Application Status
```bash
ssh ec2-user@YOUR_INSTANCE_IP 'sudo docker-compose ps'
```

### View Logs
```bash
# All services
ssh ec2-user@YOUR_INSTANCE_IP 'sudo docker-compose logs'

# Specific service
ssh ec2-user@YOUR_INSTANCE_IP 'sudo docker-compose logs frontend'
ssh ec2-user@YOUR_INSTANCE_IP 'sudo docker-compose logs backend'
ssh ec2-user@YOUR_INSTANCE_IP 'sudo docker-compose logs db'
```

### Restart Services
```bash
# All services
ssh ec2-user@YOUR_INSTANCE_IP 'sudo docker-compose restart'

# Specific service
ssh ec2-user@YOUR_INSTANCE_IP 'sudo docker-compose restart backend'
```

### Update Application
```bash
# Re-run the deployment script
./deploy.sh
```

## 🐛 Troubleshooting

### Common Issues

1. **Cannot connect via SSH**
   - Check security group allows SSH from your IP
   - Verify key pair name and file permissions
   - Ensure instance is running

2. **Services not starting**
   - Check logs: `sudo docker-compose logs`
   - Verify Docker is running: `sudo systemctl status docker`
   - Check disk space: `df -h`

3. **Application not accessible**
   - Verify security group allows HTTP (port 80)
   - Check if containers are running: `sudo docker-compose ps`
   - Test locally: `curl http://localhost` from EC2 instance

4. **Database connection issues**
   - Check if PostgreSQL container is healthy
   - Verify environment variables in docker-compose.yml
   - Check database logs: `sudo docker-compose logs db`

### Health Checks

The application includes several health check endpoints:

- **Frontend**: `http://YOUR_INSTANCE_IP/` (should show Vue.js app)
- **Backend API**: `http://YOUR_INSTANCE_IP/api/health` (should return `{"status": "ok"}`)
- **Database Ready**: `http://YOUR_INSTANCE_IP/api/readyz` (checks DB connection)

## 💰 Cost Optimization

This setup is designed for cost efficiency:

- **t2.micro instance**: Free tier eligible (750 hours/month)
- **Single instance**: All services on one machine
- **GP3 storage**: Cost-effective storage type
- **No load balancer**: Direct instance access

**Estimated monthly cost**: ~$0-10 (depending on free tier eligibility and usage)

## 🔄 Cleanup

To destroy the infrastructure and avoid charges:

```bash
cd terraform
terraform destroy
```

This will remove all AWS resources created by Terraform.

## 📝 Notes

- The setup uses Amazon Linux 2 AMI for compatibility
- Docker and Docker Compose are automatically installed via user data
- The deployment script handles application updates
- All data is persisted in Docker volumes
- The configuration supports both development and production environments

For production use, consider:
- Using RDS instead of containerized PostgreSQL
- Adding an Application Load Balancer
- Implementing auto-scaling
- Setting up monitoring and logging
- Using AWS Secrets Manager for sensitive data