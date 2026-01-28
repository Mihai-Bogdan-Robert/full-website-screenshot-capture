# Full Website Captures - Live Deployment Guide

## Monetization Strategies

### 1. Google Ads
- Display ads on the main page and results page
- Estimated revenue: $1-5 per 1000 pageviews
- Easy to implement with Google AdSense
- Consider: Non-intrusive placement to maintain UX

### 2. Freemium Model
**Free Tier:**
- 10 pages per capture
- Desktop only
- 3 captures per day
- Watermarked screenshots (optional)

**Premium Tier ($9.99/month or $79.99/year):**
- Unlimited pages per capture
- Desktop + Mobile captures
- Unlimited captures per day
- No watermarks
- Priority processing queue
- API access
- Bulk downloads

**Pro Tier ($29.99/month):**
- Everything in Premium
- 10 concurrent jobs
- Webhook notifications
- Custom branding removal
- White-label option

### 3. Pay-Per-Use Credits
- $0.01 per page captured
- Credit packs: 
  - 100 pages = $0.99 (1¢/page)
  - 500 pages = $3.99 (0.8¢/page)
  - 1000 pages = $6.99 (0.7¢/page)
  - 5000 pages = $24.99 (0.5¢/page)

### 4. API Access
- $49/month for API access
- Rate limits: 1000 requests/day
- Webhook support
- Documentation and SDKs

### 5. White-Label / Agency Licensing
- $199/month per agency
- Custom domain and branding
- Resale rights
- Dedicated support

### 6. Enterprise Solutions
- Custom pricing based on volume
- On-premise deployment
- SLA guarantees
- Dedicated infrastructure
- Custom features

## Rate Limiting & Server Protection

### Resource Limits (CRITICAL)

#### 1. Per-Job Limits
```python
MAX_PAGES_PER_JOB = {
    'free': 10,
    'premium': 500,
    'pro': 1000,
    'enterprise': 5000
}

MAX_JOB_DURATION = {
    'free': 5 * 60,      # 5 minutes
    'premium': 30 * 60,  # 30 minutes
    'pro': 60 * 60,      # 1 hour
    'enterprise': None   # Unlimited
}
```

#### 2. Per-User Limits
```python
JOBS_PER_HOUR = {
    'anonymous': 2,
    'free': 5,
    'premium': 50,
    'pro': 200,
    'enterprise': None
}

CONCURRENT_JOBS = {
    'anonymous': 1,
    'free': 1,
    'premium': 3,
    'pro': 10,
    'enterprise': 20
}
```

#### 3. Global Limits
```python
MAX_CONCURRENT_JOBS_GLOBAL = 20  # Total across all users
MAX_MEMORY_PER_CONTAINER = 2048  # 2GB (already set)
MAX_QUEUE_SIZE = 100  # Maximum jobs in queue
```

### Rate Limiting Implementation

#### IP-Based Rate Limiting (for anonymous users)
```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app,
    key_func=get_remote_address,
    default_limits=["100 per day", "20 per hour"]
)

@app.route('/api/jobs', methods=['POST'])
@limiter.limit("5 per hour")  # For anonymous users
def create_job():
    # ... existing code
```

#### User Authentication
- Implement JWT or session-based auth
- Track usage per user in database
- Different limits per tier

#### Captcha Protection
```python
# Add reCAPTCHA v3 for anonymous users
# Score < 0.5 = likely bot, show challenge or deny
```

### Server Configuration

#### Recommended VPS Specs

**Minimum (50-100 jobs/day):**
- 4 vCPUs
- 8GB RAM
- 50GB SSD
- 1TB bandwidth/month
- Cost: ~$20-40/month

**Recommended (500-1000 jobs/day):**
- 8 vCPUs
- 16GB RAM
- 100GB SSD
- 5TB bandwidth/month
- Cost: ~$80-120/month

**High Traffic (5000+ jobs/day):**
- 16+ vCPUs
- 32GB+ RAM
- 200GB+ SSD
- 10TB+ bandwidth/month
- Load balancer + multiple containers
- Cost: ~$300-500/month

#### Docker Configuration
```yaml
# docker-compose.prod.yml
services:
  web:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 2G
        reservations:
          cpus: '1.0'
          memory: 1G
      replicas: 3  # Multiple containers
    restart: always
    environment:
      - MAX_WORKERS=4  # Increase workers
```

### Monitoring & Alerts

#### Essential Monitoring
1. **Resource Usage:**
   - CPU usage > 80%
   - Memory usage > 85%
   - Disk space < 10%

2. **Application Metrics:**
   - Jobs completed/failed ratio
   - Average job duration
   - Queue length
   - Active connections

3. **Alerts:**
   - Email/SMS when limits exceeded
   - Auto-scaling triggers
   - Crash notifications

#### Tools
- **Monitoring:** Prometheus + Grafana
- **Logging:** ELK Stack (Elasticsearch, Logstash, Kibana)
- **Uptime:** UptimeRobot or Pingdom
- **Error Tracking:** Sentry

### Security Considerations

1. **HTTPS Only** - Use Let's Encrypt
2. **CORS** - Whitelist allowed origins
3. **Input Validation** - Sanitize all URLs
4. **DDoS Protection** - Cloudflare or similar
5. **API Keys** - For authenticated users
6. **Rate Limiting** - Redis-backed rate limiter
7. **Content Security Policy** - Prevent XSS
8. **Regular Updates** - Keep dependencies updated

### Database for Production

**PostgreSQL Schema:**
```sql
-- Users table
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    tier VARCHAR(50) DEFAULT 'free',
    credits INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    last_login TIMESTAMP
);

-- Jobs tracking
CREATE TABLE jobs (
    id VARCHAR(50) PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    url TEXT NOT NULL,
    status VARCHAR(50),
    pages_captured INTEGER DEFAULT 0,
    mode VARCHAR(50),
    device VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,
    error TEXT
);

-- Usage tracking
CREATE TABLE usage_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    ip_address INET,
    job_id VARCHAR(50),
    pages_captured INTEGER,
    timestamp TIMESTAMP DEFAULT NOW()
);

-- Create indexes
CREATE INDEX idx_jobs_user_id ON jobs(user_id);
CREATE INDEX idx_jobs_created_at ON jobs(created_at);
CREATE INDEX idx_usage_timestamp ON usage_logs(timestamp);
```

### Cost Breakdown Example

#### VPS Costs
- Server: $80/month (8 vCPUs, 16GB RAM)
- Cloudflare Pro: $20/month (DDoS protection)
- Database: $25/month (Managed PostgreSQL)
- Backups: $10/month
- Domain: $15/year
- SSL: Free (Let's Encrypt)
- **Total: ~$135/month**

#### Break-Even Analysis
- Need ~14 premium users ($9.99/month) to break even
- Or ~1350 credit purchases ($0.99 each)
- Mix of both + ads = sustainable

### Scaling Strategy

**Phase 1: Single Server (0-1000 jobs/day)**
- 1 VPS with Docker
- PostgreSQL on same server
- Basic monitoring

**Phase 2: Multiple Containers (1000-5000 jobs/day)**
- Docker Swarm or Kubernetes
- Separate database server
- Redis for queuing
- Load balancer

**Phase 3: Distributed (5000+ jobs/day)**
- Multiple regions
- CDN for static assets
- Auto-scaling
- Dedicated job queue (RabbitMQ/Redis)
- Separate Playwright cluster

### Launch Checklist

- [ ] Set up VPS and domain
- [ ] Configure HTTPS with Let's Encrypt
- [ ] Implement user authentication
- [ ] Set up PostgreSQL database
- [ ] Implement rate limiting
- [ ] Add Captcha for anonymous users
- [ ] Set up monitoring and alerts
- [ ] Configure backups (daily)
- [ ] Write Terms of Service and Privacy Policy
- [ ] Set up payment processing (Stripe)
- [ ] Implement usage tracking
- [ ] Add API documentation
- [ ] Set up error tracking (Sentry)
- [ ] Configure Cloudflare
- [ ] Test under load
- [ ] Prepare marketing materials
- [ ] Set up customer support (email/chat)

### Marketing Ideas

1. **SEO Optimization**
   - Blog about website testing, QA
   - Tutorials and use cases

2. **Social Media**
   - Twitter/X for developers
   - LinkedIn for agencies
   - Reddit (r/webdev, r/QA)

3. **Partnerships**
   - Web development agencies
   - QA testing companies
   - Design firms

4. **Content Marketing**
   - "How to test responsive design"
   - "Website QA checklist"
   - Case studies

5. **Free Tools**
   - Single page screenshot (free, unlimited)
   - Drives traffic to full tool
