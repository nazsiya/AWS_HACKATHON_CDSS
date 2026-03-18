# CDSS Operational Runbooks (Req 7.3)

Operational procedures for the CDSS engineering and DevOps teams.

## 1. Deployment (CI/CD & Manual)
### CI/CD Flow
1. **Trigger**: Push to `main` or `release/*` branches.
2. **Action**: GitHub Actions (`.github/workflows/deploy.yml`) runs linting, tests, and Terraform Apply.
3. **Verification**: Confirm success via CloudWatch "Deployment Status" dashboard.

### Manual Lambda Update
```bash
# Zip the source
cd src && zip -r ../lambda_payload.zip .
# Update via AWS CLI
aws lambda update-function-code --function-name cdss-dev-api-router --zip-file fileb://../lambda_payload.zip
```

## 2. Scaling Procedures
### Backend (Lambda)
- **Monitoring**: Check `ConcurrentExecutions` in the CDSS Dashboard.
- **Action**: If approaching limit, request AWS Service Quota increase or adjust Provisioned Concurrency in `lambda.tf`.

### Database (Aurora)
- **Vertical Scaling**: Modify `db_instance_class` in `rds.tf` (e.g., `db.t3.medium` to `db.r6g.large`).
- **Read Replicas**: Increment `replica_count` in `rds.tf` for high read volume.

## 3. Incident Response
### High Latency (Alarm: `api-latency`)
1. Check Bedrock model availability in `ap-south-1`.
2. Review Lambda `Duration` and `Throttles`.
3. If database-bound, check for long-running queries in Aurora Performance Insights.

### Database Connection Failures
1. Verify SSH Tunnel status for local development.
2. Check IAM Policy roles for the Lambda executor.
3. Ensure `DATABASE_URL` in Secrets Manager matches the current host.

## 4. Rollback Strategies
### API Rollback
Using Lambda Versions:
```bash
# Point the 'prod' alias to the previous successful version
aws lambda update-alias --function-name cdss-dev-api-router --name prod --function-version <PREVIOUS_VERSION>
```

### Terraform Rollback
```bash
git checkout <PREVIOUS_STABLE_COMMIT>
terraform apply
```

---
*On-Call Rotation: clinical-it-support@cdss.ai*
