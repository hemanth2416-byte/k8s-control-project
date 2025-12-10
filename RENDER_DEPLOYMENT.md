# Kubernetes Control Panel - Render Deployment Guide

## 📋 Prerequisites

1. **GitHub Account** - Push code to GitHub
2. **Render.com Account** - Free tier available
3. **K8s Kubeconfig** - If you want K8s functionality on Render

---

## 🚀 Quick Deploy to Render

### Step 1: Push to GitHub

```bash
cd C:\Users\heman\k8s-control-project

# Initialize git (if not already done)
git init
git add .
git commit -m "K8s Control Panel - Black & Gold Theme"
git remote add origin https://github.com/hemanth2416-byte/k8s-control-project
git push -u origin main
```

### Step 2: Deploy on Render

1. Go to **https://render.com** and sign up (free)
2. Click **New +** → **Web Service**
3. Select your GitHub repository
4. Fill in details:
   - **Name:** `k8s-control-panel`
   - **Runtime:** Python
   - **Build Command:** `pip install -r controller-api/requirements.txt`
   - **Start Command:** `cd controller-api && uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Click **Deploy**

### Step 3: Share the Link

Your app will be available at:
```
https://k8s-control-panel.onrender.com/ui
```

Share this link with your team in Microsoft Teams! ✨

---

## ⚙️ Configuration (Optional)

### For Kubernetes Integration:

1. Upload your `~/.kube/config` to Render as a secret file
2. Set environment variable: `KUBECONFIG=/var/data/kubeconfig`

### For Kafka Integration:

Set environment variable in Render:
```
KAFKA_BOOTSTRAP_SERVERS=your-kafka-server:9092
```

---

## 📊 Features

✅ **Black & Gold Theme** - Premium appearance
✅ **Pod Status Viewer** - See running pods
✅ **Logs Viewer** - View pod logs in real-time
✅ **Deployment Scaling** - Scale replicas up/down
✅ **Auto-scaling (HPA)** - Configure auto-scaling
✅ **Events Timeline** - Monitor cluster events
✅ **Resource Usage** - View CPU/Memory usage
✅ **Rollback Support** - Rollback to previous versions
✅ **Cluster Statistics** - Overview of cluster health

---

## 🔗 Your Public Link

Once deployed on Render, your team can access:

```
https://k8s-control-panel.onrender.com/ui
```

No installation needed - just share the link! 🎉

---

## 📝 Notes

- **Free tier on Render:** 0.5 GB RAM, no credit card required
- **Timeout:** Auto-spins down after 15 min inactivity (cold start on next request)
- **K8s access:** Requires kubeconfig uploaded to Render
- **Kafka:** Optional, dashboard works without it

---

## ❓ Troubleshooting

**"Error: Cannot connect to K8s"**
- Upload your kubeconfig file to Render as environment secret
- Or skip K8s features and use dashboard for viewing logs only

**"Service is slow"**
- Render free tier may have cold starts
- Upgrade to paid tier for guaranteed uptime

**"Kafka not connecting"**
- This is fine, dashboard still works for viewing and getting status
- Kafka is only needed for sending commands to Kafka topics

---

## 📞 Support

For issues or questions, check:
- Render logs in dashboard
- K8s configuration
- Network connectivity to K8s cluster

---

Made with ❤️ | Black & Gold Theme 🎨
