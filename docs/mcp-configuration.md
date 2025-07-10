# MCP Monitoring System Configuration

This document explains how to configure the MCP (Model Context Protocol) monitoring system for PipeWise.

## Overview

The MCP monitoring system provides comprehensive observability for all external service integrations including:

- **Health Monitoring**: Periodic health checks with automated failure detection
- **Alert Management**: Intelligent alerting with multiple notification channels
- **Performance Metrics**: Response time tracking and performance analysis
- **Configuration Management**: Environment-based configuration with validation

## Environment Variables

### MCP System Settings

```bash
# Core monitoring settings
MCP_HEALTH_CHECK_INTERVAL=300        # Health check interval in seconds (5 minutes)
MCP_HEALTH_CHECK_TIMEOUT=30          # Health check timeout in seconds
MCP_HEALTH_ALERT_THRESHOLD=3         # Consecutive failures before alerting
MCP_ALERT_CHECK_INTERVAL=60          # Alert check interval in seconds
MCP_MAX_ACTIVE_ALERTS=1000           # Maximum active alerts to maintain
MCP_MAX_DATA_POINTS=100000           # Maximum performance data points to keep
MCP_AGGREGATION_INTERVAL=60          # Metrics aggregation interval in seconds
MCP_RETENTION_DAYS=7                 # How many days to retain metrics
MCP_LOG_LEVEL=INFO                   # Logging level (DEBUG, INFO, WARNING, ERROR)
MCP_ENABLE_STRUCTURED_LOGGING=true   # Enable structured JSON logging
MCP_METRICS_RETENTION_HOURS=24       # How long to retain in-memory metrics
```

### Service Configurations

#### SendGrid (Email Service)
```bash
SENDGRID_ENABLED=true
SENDGRID_API_KEY=your_sendgrid_api_key_here
SENDGRID_BASE_URL=https://api.sendgrid.com/v3
SENDGRID_FROM_EMAIL=noreply@yourcompany.com
```

#### Twitter Integration
```bash
TWITTER_ENABLED=true
TWITTER_BEARER_TOKEN=your_twitter_bearer_token_here
TWITTER_API_KEY=your_twitter_api_key_here
TWITTER_API_SECRET=your_twitter_api_secret_here
TWITTER_ACCESS_TOKEN=your_twitter_access_token_here
TWITTER_ACCESS_TOKEN_SECRET=your_twitter_access_token_secret_here
TWITTER_BASE_URL=https://api.twitter.com/2
```

#### Calendly Integration
```bash
CALENDLY_ENABLED=true
CALENDLY_ACCESS_TOKEN=your_calendly_access_token_here
CALENDLY_BASE_URL=https://api.calendly.com
CALENDLY_WEBHOOK_SIGNING_KEY=your_calendly_webhook_signing_key_here
```

#### Google Calendar Integration
```bash
GOOGLE_CALENDAR_ENABLED=true
GOOGLE_ACCESS_TOKEN=your_google_access_token_here
GOOGLE_REFRESH_TOKEN=your_google_refresh_token_here
GOOGLE_CLIENT_ID=your_google_client_id_here
GOOGLE_CLIENT_SECRET=your_google_client_secret_here
GOOGLE_CALENDAR_BASE_URL=https://www.googleapis.com/calendar/v3
```

#### Pipedrive CRM Integration
```bash
PIPEDRIVE_ENABLED=true
PIPEDRIVE_API_TOKEN=your_pipedrive_api_token_here
PIPEDRIVE_BASE_URL=https://api.pipedrive.com/v1
PIPEDRIVE_COMPANY_DOMAIN=your_company_domain_here
```

#### Salesforce Integration
```bash
SALESFORCE_ENABLED=true
SALESFORCE_ACCESS_TOKEN=your_salesforce_access_token_here
SALESFORCE_REFRESH_TOKEN=your_salesforce_refresh_token_here
SALESFORCE_INSTANCE_URL=your_salesforce_instance_url_here
SALESFORCE_CLIENT_ID=your_salesforce_client_id_here
SALESFORCE_CLIENT_SECRET=your_salesforce_client_secret_here
SALESFORCE_API_VERSION=v54.0
```

#### Zoho CRM Integration
```bash
ZOHO_ENABLED=true
ZOHO_ACCESS_TOKEN=your_zoho_access_token_here
ZOHO_REFRESH_TOKEN=your_zoho_refresh_token_here
ZOHO_API_DOMAIN=www.zohoapis.com
ZOHO_CLIENT_ID=your_zoho_client_id_here
ZOHO_CLIENT_SECRET=your_zoho_client_secret_here
ZOHO_ORG_ID=your_zoho_org_id_here
```

#### Pipedream Integration
```bash
PIPEDREAM_ENABLED=true
PIPEDREAM_API_KEY=your_pipedream_api_key_here
PIPEDREAM_BASE_URL=https://api.pipedream.com/v1
PIPEDREAM_WORKSPACE_ID=your_pipedream_workspace_id_here
```

#### PipeWise API Self-Monitoring
```bash
PIPEWISE_API_MONITORING_ENABLED=true
PIPEWISE_API_BASE_URL=http://localhost:8000
PIPEWISE_API_KEY=your_pipewise_api_key_here
PIPEWISE_HEALTH_ENDPOINT=/health
```

### Alert Notification Configuration

#### Email Alerts
```bash
ALERT_EMAIL_ENABLED=true
ALERT_SMTP_SERVER=smtp.gmail.com
ALERT_SMTP_PORT=587
ALERT_SMTP_USERNAME=your_email_username_here
ALERT_SMTP_PASSWORD=your_email_password_here
ALERT_FROM_EMAIL=alerts@yourcompany.com
ALERT_TO_EMAILS=admin@yourcompany.com,ops@yourcompany.com
ALERT_SMTP_TLS=true
```

#### Slack Alerts
```bash
ALERT_SLACK_ENABLED=false
ALERT_SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK
ALERT_SLACK_CHANNEL=#alerts
ALERT_SLACK_USERNAME=PipeWise Alert Bot
```

#### Webhook Alerts
```bash
ALERT_WEBHOOK_ENABLED=false
ALERT_WEBHOOK_URL=https://your-webhook-endpoint.com/alerts
ALERT_WEBHOOK_METHOD=POST
ALERT_WEBHOOK_TOKEN=your_webhook_auth_token_here
```

## Configuration Best Practices

### Health Check Intervals

- **Production**: 300 seconds (5 minutes) for regular monitoring
- **Development**: 60 seconds (1 minute) for faster feedback
- **Critical Services**: 30 seconds for immediate detection

### Alert Thresholds

- **Standard**: 3 consecutive failures balances sensitivity and false positives
- **Critical Services**: 1-2 failures for immediate attention
- **Less Critical**: 5+ failures to reduce noise

### Performance Monitoring

- **Data Points**: 100,000 provides good historical analysis
- **Aggregation**: 60-second intervals balance accuracy with performance
- **Retention**: 7 days provides sufficient historical data

### Security Considerations

1. **Never commit credentials** to version control
2. **Use environment variables** for all sensitive configuration
3. **Rotate credentials regularly** for external services
4. **Monitor for credential leaks** in logs and alerts
5. **Use least privilege** for API keys and tokens

## Setup Instructions

1. **Copy the configuration template** to your `.env` file
2. **Replace all placeholder values** with your actual credentials
3. **Disable unused services** by setting `SERVICE_ENABLED=false`
4. **Configure alert channels** based on your notification preferences
5. **Test the configuration** using the health check endpoints
6. **Review logs** for any configuration validation errors

## Health Check Endpoints

The MCP monitoring system provides several endpoints for checking system health:

- `GET /health/mcp` - Overall MCP system health
- `GET /health/mcp/services` - Individual service health status
- `GET /health/mcp/alerts` - Active alerts summary
- `GET /health/mcp/metrics` - Performance metrics overview

## Configuration Validation

The system automatically validates configuration on startup and provides detailed error messages for:

- **Missing required credentials** for enabled services
- **Invalid configuration values** (URLs, timeouts, etc.)
- **Network connectivity issues** during health checks
- **Authentication failures** with external services

## Monitoring Dashboard

Access the monitoring dashboard at:
- Development: `http://localhost:8000/health/mcp`
- Production: `https://your-domain.com/health/mcp`

The dashboard provides:
- **Real-time service status** with color-coded indicators
- **Historical performance metrics** with charts and graphs
- **Active alerts** with severity levels and timestamps
- **Configuration overview** with validation status

## Troubleshooting

### Common Issues

1. **Service timeouts**: Increase `MCP_HEALTH_CHECK_TIMEOUT`
2. **Too many alerts**: Increase `MCP_HEALTH_ALERT_THRESHOLD`
3. **Missing metrics**: Check `MCP_METRICS_RETENTION_HOURS`
4. **Authentication errors**: Verify API keys and tokens
5. **Network issues**: Check firewall and DNS settings

### Log Analysis

Enable debug logging for detailed troubleshooting:
```bash
MCP_LOG_LEVEL=DEBUG
MCP_ENABLE_STRUCTURED_LOGGING=true
```

### Performance Optimization

For high-traffic environments:
- Increase `MCP_MAX_DATA_POINTS` for more historical data
- Decrease `MCP_AGGREGATION_INTERVAL` for more frequent analysis
- Use Redis for caching frequently accessed metrics
- Consider horizontal scaling for multiple instances

## Support

For additional support and configuration assistance:
- Review the health check endpoints for real-time status
- Check application logs for detailed error messages
- Use the configuration validation API to verify settings
- Contact the PipeWise support team for complex configurations 