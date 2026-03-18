## CDSS AI Agent Layer Implementation Rules

### AWS Integration Standards
- Use existing Terraform configurations in /infra for all AWS resources
- Deploy Lambda functions within VPC using private subnets (${region}a, ${region}b)
- Store all agent state and conversation data in Aurora PostgreSQL
- Use S3 buckets appropriately: main (assets), documents (clinical docs), corpus (training data)
- Access Bedrock through configured IAM policies (regions: ap-south-1, us-east-1, us-east-2, us-west-2)
- Store all secrets in AWS Secrets Manager (bedrock_config, rds_config)
- Use SSM Parameter Store for feature flags (transcriptions_enabled, translation_enabled, abdm_integration_enabled)
- Implement EventBridge for all inter-agent communication via cdss_eventbridge module
- Use existing SNS/SQS infrastructure with DLQ for reliable message delivery

### MCP Communication Standards
- All agent communication must use Model Context Protocol via EventBridge
- Define strict message schemas for each agent interaction type
- Implement message validation and schema versioning
- Maintain complete audit trails of all inter-agent communications
- Handle communication failures with retry logic and DLQ
- Ensure all messages include trace IDs for end-to-end tracking

### Data Storage Architecture
- **Aurora PostgreSQL**: Store patient records, conversation summaries, medical entities, adherence data
- **S3 Documents Bucket**: Store raw conversation audio, clinical documents, surgery videos/images
- **S3 Corpus Bucket**: Store anonymized training data, model artifacts, medical knowledge bases
- **Secrets Manager**: Store API keys, database credentials, model configurations
- **SSM Parameter Store**: Store feature flags, operational configurations

### Agent-Specific Storage Requirements

#### Patient Agent
- Patient profiles with ABHA ID integration
- Complete medical history with visit chronology
- Surgery readiness assessments
- Risk factor profiles

#### Surgery Agent
- Surgery classifications and requirements
- Real-time procedure guidance data
- Complication patterns and responses
- Surgical instrument databases

#### Resource Agent
- Real-time staff availability tracking
- Equipment status and maintenance history
- Operating room schedules
- Inventory management data

#### Scheduling Agent
- Optimized surgery schedules
- Replacement specialist algorithms
- Workload balancing metrics
- Historical scheduling patterns

#### Patient Engagement Agent
- Conversation transcripts (raw and processed)
- Extracted medical entities
- Medication reminder schedules
- Adherence tracking data

### Code Quality Standards
- Python 3.11+ with strict type hints
- Pydantic models for all data validation
- SQLAlchemy 2.0 for database interactions
- AWS Lambda Powertools for observability
- Comprehensive error handling with custom exceptions
- Unit tests with 80%+ coverage
- Integration tests for all AWS services
- Docstrings for all public interfaces

### Observability Requirements
- CloudWatch Logs with structured JSON logging
- X-Ray tracing for all Lambda invocations
- Custom metrics for agent performance
- Dashboards for agent health and throughput
- Alerts for error rates and latency spikes
- Audit logging for all medical data access