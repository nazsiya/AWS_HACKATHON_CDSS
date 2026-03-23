# Known Issues Log
Tested by Member 4 on 2026-03-23

### Doctor Dashboard - CORS Errors (S3 URL)
URL: http://cdss-dev-746412758276.s3-website.ap-south-1.amazonaws.com
Error: Cannot reach API - CORS policy blocking API calls
Status: Needs fix on API Gateway side - Member 1 to fix

### Doctor Dashboard - CORS Errors (CloudFront URL)
URL: https://d2vd4sz7q1csya.cloudfront.net
Error: CORS still blocked even via CloudFront
Affected endpoints:
- /prod/api/v1/tasks
- /prod/api/v1/patients (500 Internal Server Error)
- /prod/api/v1/surgeries (500 Internal Server Error)
- /prod/api/v1/activity
Status: API Gateway needs Access-Control-Allow-Origin headers - Member 1 to fix

### Patient Portal - Access Denied
URL: http://cdss-dev-corpus-746412758276.s3-website.ap-south-1.amazonaws.com
Error: 403 Forbidden - AccessDenied
Status: S3 bucket not configured for public access - Member 3 to fix
