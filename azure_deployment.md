# Azure Deployment Guide for Zoom Extractor

## 🎯 Recommended: Azure Virtual Machine

### Step 1: Create Azure VM

```bash
# Using Azure CLI (install from https://docs.microsoft.com/en-us/cli/azure/install-azure-cli)

# Login to Azure
az login

# Create resource group
az group create --name zoom-extractor-rg --location eastus

# Create VM (Ubuntu 20.04 LTS)
az vm create \
  --resource-group zoom-extractor-rg \
  --name zoom-extractor-vm \
  --image Ubuntu2004 \
  --size Standard_D4s_v3 \
  --admin-username azureuser \
  --generate-ssh-keys \
  --storage-sku Premium_LRS \
  --public-ip-sku Standard
```

### Step 2: Configure VM

```bash
# SSH into your VM
ssh azureuser@<your-vm-ip>

# Update system
sudo apt update && sudo apt upgrade -y

# Install Python and dependencies
sudo apt install -y python3 python3-pip python3-venv git

# Install Azure CLI (optional, for managing resources)
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash
```

### Step 3: Deploy Zoom Extractor

```bash
# Clone the repository
git clone https://github.com/silicoon84/zoomextractor.git
cd zoomextractor

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp env.example .env
nano .env  # Add your Zoom credentials

# Test installation
python test_installation.py
```

### Step 4: Run Extraction

```bash
# Quick count first
python total_count.py

# Run extraction
python zoom_extract.py --log-file extraction.log

# Or run in background
nohup python zoom_extract.py --log-file extraction.log > output.log 2>&1 &

# Monitor progress
tail -f extraction.log
```

## 💰 Cost Optimization

### VM Sizes and Costs (East US, pay-as-you-go):

| Size | vCPUs | RAM | Storage | Cost/hour | Best For |
|------|-------|-----|---------|-----------|----------|
| Standard_B2s | 2 | 4GB | 8GB SSD | ~$0.04 | Small datasets |
| Standard_D2s_v3 | 2 | 8GB | 16GB SSD | ~$0.10 | Medium datasets |
| Standard_D4s_v3 | 4 | 16GB | 32GB SSD | ~$0.20 | Large datasets |
| Standard_D8s_v3 | 8 | 32GB | 64GB SSD | ~$0.40 | Very large datasets |

### Cost-Saving Tips:

1. **Stop VM when not in use**:
   ```bash
   az vm deallocate --resource-group zoom-extractor-rg --name zoom-extractor-vm
   ```

2. **Start VM when needed**:
   ```bash
   az vm start --resource-group zoom-extractor-rg --name zoom-extractor-vm
   ```

3. **Use Spot VMs** (up to 90% cheaper):
   ```bash
   az vm create --name zoom-extractor-vm --priority Spot --max-price -1
   ```

## 🗄️ Storage Options

### 1. **VM Disk (Simplest)**
- **Pros**: Easy, no additional setup
- **Cons**: Limited size, data lost if VM deleted
- **Best for**: Temporary extractions

### 2. **Azure Files (Recommended)**
- **Pros**: Persistent, can be shared, resizable
- **Cons**: Slightly more complex setup
- **Best for**: Long-term storage

```bash
# Create storage account
az storage account create \
  --name zoomextractorstorage \
  --resource-group zoom-extractor-rg \
  --location eastus \
  --sku Standard_LRS

# Create file share
az storage share create \
  --name zoom-recordings \
  --account-name zoomextractorstorage
```

### 3. **Azure Blob Storage**
- **Pros**: Very cheap, massive scale
- **Cons**: More complex for file operations
- **Best for**: Archival, backup

## 🔧 Alternative: Azure Container Instances (ACI)

If you prefer containers:

```bash
# Create container registry
az acr create \
  --resource-group zoom-extractor-rg \
  --name zoomextractoracr \
  --sku Basic

# Build and push container
docker build -t zoomextractoracr.azurecr.io/zoom-extractor .
az acr login --name zoomextractoracr
docker push zoomextractoracr.azurecr.io/zoom-extractor

# Run container
az container create \
  --resource-group zoom-extractor-rg \
  --name zoom-extractor-container \
  --image zoomextractoracr.azurecr.io/zoom-extractor \
  --cpu 2 \
  --memory 8 \
  --restart-policy Never
```

## 📋 Pre-deployment Checklist

- [ ] Azure account with billing enabled
- [ ] Zoom S2S OAuth app configured
- [ ] Zoom credentials ready
- [ ] Estimate of data size needed
- [ ] Decide on VM size based on data volume

## 🚀 Quick Start Commands

```bash
# 1. Create VM
az vm create --resource-group zoom-extractor-rg --name zoom-extractor-vm --image Ubuntu2004 --size Standard_D4s_v3 --admin-username azureuser --generate-ssh-keys

# 2. SSH and setup
ssh azureuser@<vm-ip>
sudo apt update && sudo apt install -y python3 python3-pip python3-venv git
git clone https://github.com/silicoon84/zoomextractor.git
cd zoomextractor
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 3. Configure and run
cp env.example .env  # Add your Zoom credentials
python total_count.py  # Check data volume
python zoom_extract.py --log-file extraction.log  # Start extraction
```

## 💡 Pro Tips

1. **Use screen/tmux** for long-running processes:
   ```bash
   sudo apt install screen
   screen -S extraction
   python zoom_extract.py --log-file extraction.log
   # Ctrl+A, D to detach
   screen -r extraction  # Reattach
   ```

2. **Monitor costs**:
   ```bash
   az consumption usage list --start-date 2024-01-01 --end-date 2024-01-31
   ```

3. **Automate VM shutdown**:
   ```bash
   # Add to crontab for automatic shutdown after 24 hours
   echo "0 0 * * * az vm deallocate --resource-group zoom-extractor-rg --name zoom-extractor-vm" | crontab -
   ```

This approach gives you a powerful, scalable solution for extracting Zoom recordings with full control over the environment!
