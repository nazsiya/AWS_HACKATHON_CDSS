import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { CdssStack } from '../lib/cdss-stack';

const app = new cdk.App();
new CdssStack(app, 'CdssStack', {
    env: {
        account: process.env.CDK_DEFAULT_ACCOUNT,
        region: process.env.CDK_DEFAULT_REGION || 'ap-south-1'
    },
    description: 'CDSS — Clinical Decision Support System. Multi-agent architecture with Bedrock and CDK.'
});
