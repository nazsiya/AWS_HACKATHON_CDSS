import * as cdk from 'aws-cdk-lib';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as rds from 'aws-cdk-lib/aws-rds';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as apigateway from 'aws-cdk-lib/aws-apigateway';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as events from 'aws-cdk-lib/aws-events';
import * as targets from 'aws-cdk-lib/aws-events-targets';
import { Construct } from 'constructs';
import * as path from 'path';
import * as fs from 'fs';

function copyDirContents(srcDir: string, destDir: string): void {
    // Copy the *contents* of `srcDir` into `destDir` (not the `srcDir` folder itself),
    // so Lambda handler files remain at the bundle root.
    for (const entry of fs.readdirSync(srcDir, { withFileTypes: true })) {
        const src = path.join(srcDir, entry.name);
        const dest = path.join(destDir, entry.name);
        if (entry.isDirectory()) {
            fs.cpSync(src, dest, { recursive: true });
        } else {
            fs.copyFileSync(src, dest);
        }
    }
}

export class CdssStack extends cdk.Stack {
    constructor(scope: Construct, id: string, props?: cdk.StackProps) {
        super(scope, id, props);

        // ----------------------------------------------------------------
        // 0. Stack Parameters (avoid naming collisions)
        // ----------------------------------------------------------------
        const envName = new cdk.CfnParameter(this, 'EnvName', {
            type: 'String',
            default: 'dev',
            description: 'Environment name (dev, staging, prod)',
        });
        const agentEventBusName = `cdss-agent-bus-${envName.valueAsString}`;

        // ----------------------------------------------------------------
        // 1. Network Layer
        // ----------------------------------------------------------------
        const vpc = new ec2.Vpc(this, 'CdssVpc', {
            maxAzs: 2,
            subnetConfiguration: [
                { name: 'Public', subnetType: ec2.SubnetType.PUBLIC },
                { name: 'Private', subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS },
                { name: 'Isolated', subnetType: ec2.SubnetType.PRIVATE_ISOLATED },
            ],
        });

        // ----------------------------------------------------------------
        // 2. Security Groups
        // ----------------------------------------------------------------
        const dbSecurityGroup = new ec2.SecurityGroup(this, 'DbSecurityGroup', {
            vpc,
            description: 'Allow PostgreSQL access from Lambda',
            allowAllOutbound: true,
        });

        const lambdaSecurityGroup = new ec2.SecurityGroup(this, 'LambdaSecurityGroup', {
            vpc,
            description: 'Security group for backend Lambdas',
            allowAllOutbound: true,
        });

        dbSecurityGroup.addIngressRule(
            lambdaSecurityGroup,
            ec2.Port.tcp(5432),
            'Allow Lambda access to PostgreSQL'
        );

        // ----------------------------------------------------------------
        // 3. Data Layer — Aurora PostgreSQL Serverless v2
        // ----------------------------------------------------------------
        const cluster = new rds.DatabaseCluster(this, 'CdssDatabase', {
            engine: rds.DatabaseClusterEngine.auroraPostgres({
                // CDK constants may lag behind regional Aurora patch versions.
                // ap-south-1 supports Aurora PostgreSQL 15.14; use an explicit version string.
                version: rds.AuroraPostgresEngineVersion.of('15.14', '15'),
            }),
            vpc,
            vpcSubnets: { subnetType: ec2.SubnetType.PRIVATE_ISOLATED },
            securityGroups: [dbSecurityGroup],
            writer: rds.ClusterInstance.serverlessV2('writer'),
            serverlessV2MinCapacity: 0.5,
            serverlessV2MaxCapacity: 2,
            defaultDatabaseName: 'cdssdb',
            removalPolicy: cdk.RemovalPolicy.DESTROY,
        });

        // Fail fast if CDK did not auto-create a secret for the cluster
        if (!cluster.secret) {
            throw new Error('Aurora cluster did not produce a Secrets Manager secret. Cannot continue.');
        }
        const rdsSecret = cluster.secret;

        // ----------------------------------------------------------------
        // 4. DynamoDB — Agent Sessions
        // ----------------------------------------------------------------
        const sessionsTable = new dynamodb.Table(this, 'SessionsTable', {
            partitionKey: { name: 'session_id', type: dynamodb.AttributeType.STRING },
            billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
            timeToLiveAttribute: 'ttl',
            tableName: `cdss-agent-sessions-${envName.valueAsString}`,
        });
        sessionsTable.applyRemovalPolicy(cdk.RemovalPolicy.DESTROY);

        // ----------------------------------------------------------------
        // 5. Shared IAM Policies
        // ----------------------------------------------------------------
        const bedrockPolicy = new iam.PolicyStatement({
            actions: ['bedrock:InvokeModel', 'bedrock:InvokeModelWithResponseStream'],
            resources: ['*'], // In production, scoped to specific models
        });

        // ----------------------------------------------------------------
        // 6. Shared Lambda Layer
        // ----------------------------------------------------------------
        const sharedLayer = new lambda.LayerVersion(this, 'SharedLayer', {
            // Package the parent directory so the layer contains `/opt/shared/...`
            // and handlers can do `from shared import ...`.
            code: lambda.Code.fromAsset(path.join(__dirname, '../../backend/agents')),
            compatibleRuntimes: [lambda.Runtime.PYTHON_3_11],
            description: 'Shared utilities for CDSS agents',
        });

        // ----------------------------------------------------------------
        // 6b. CDSS package Layer
        //     Agent Lambdas import `cdss.*` (e.g., audit logger uses `cdss.db.session`).
        // ----------------------------------------------------------------
        const cdssLayer = new lambda.LayerVersion(this, 'CdssPackageLayer', {
            code: lambda.Code.fromAsset(path.join(__dirname, '../../src')),
            compatibleRuntimes: [lambda.Runtime.PYTHON_3_11],
            description: 'Shared CDSS Python package for agent Lambdas',
        });

        // ----------------------------------------------------------------
        // 7. Common DB environment variables
        //    ALL Lambdas that touch the DB receive the same contract:
        //      RDS_CONFIG_SECRET_NAME  — secret name read by get_rds_config()
        //      AWS_REGION              — required by boto3 / IAM token generation
        //
        //    NOTE: DB_SECRET_ARN / DB_CLUSTER_ARN are intentionally omitted.
        //    The application code (src/cdss/config/secrets.py) does NOT read
        //    those variables; it reads RDS_CONFIG_SECRET_NAME.
        // ----------------------------------------------------------------
        const dbEnv = {
            RDS_CONFIG_SECRET_NAME: rdsSecret.secretName,
            DB_HOST: cluster.clusterEndpoint.hostname,
            DB_PORT: '5432',
            DB_NAME: 'cdssdb',
            DB_USER: rdsSecret.secretValueFromJson('username').unsafeUnwrap(),
        };

        // ----------------------------------------------------------------
        // 8. Agent Lambda factory
        // ----------------------------------------------------------------
        const createAgent = (name: string, folder: string): lambda.Function => {
            const fn = new lambda.Function(this, `${name}Function`, {
                runtime: lambda.Runtime.PYTHON_3_11,
                handler: 'handler.lambda_handler',
                code: lambda.Code.fromAsset(path.join(__dirname, `../../backend/agents/${folder}`)),
                vpc,
                vpcSubnets: { subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS },
                securityGroups: [lambdaSecurityGroup],
                environment: {
                    SESSIONS_TABLE: sessionsTable.tableName,
                    EVENT_BUS_NAME: agentEventBusName,
                    ...dbEnv,
                },
                layers: [sharedLayer, cdssLayer],
                timeout: cdk.Duration.seconds(30),
            });
            fn.addToRolePolicy(bedrockPolicy);
            sessionsTable.grantReadWriteData(fn);
            cluster.grantConnect(fn, rdsSecret.secretValueFromJson('username').toString());
            rdsSecret.grantRead(fn);
            return fn;
        };

        // ----------------------------------------------------------------
        // 9. Agent Lambdas
        // ----------------------------------------------------------------
        const supervisorAgent = createAgent('Supervisor', 'supervisor');
        const patientAgent = createAgent('Patient', 'patient');
        const surgeryAgent = createAgent('SurgeryPlanning', 'surgery_planning');
        // ... Repeat for other agents (OMITTED for brevity in this tech preview)

        // ----------------------------------------------------------------
        // 10. EventBus — Inter-Agent Communication
        // ----------------------------------------------------------------
        const eventBus = new events.EventBus(this, 'CdssEventBus', {
            eventBusName: agentEventBusName,
        });

        new events.Rule(this, 'SupervisorToSubAgentRule', {
            eventBus,
            eventPattern: { detailType: ['AgentActionRequested'] },
            targets: [new targets.LambdaFunction(patientAgent)],
        });

        // Supervisor publishes routing events to EventBridge via EventPublisher.publish().
        eventBus.grantPutEventsTo(supervisorAgent);

        // ----------------------------------------------------------------
        // 11. Dashboard REST Lambda
        //     Uses the SAME DB config contract as every other Lambda.
        // ----------------------------------------------------------------
        // NOTE: Docker-based bundling requires a local Docker install, which may
        // not exist in the deploy environment. Instead, we create a small staging
        // directory at synth-time and copy:
        //   - backend/api/rest/*  -> bundle root
        //   - src/cdss/*         -> bundle root/cdss/
        // so `from cdss.config.secrets import ...` works in production.
        const dashboardRestSrcDir = path.join(__dirname, '../../backend/api/rest');
        const dashboardBundleDir = path.join(__dirname, '..', 'lambda-bundle', 'dashboard');
        const cdssSrcDir = path.join(__dirname, '../../src/cdss');

        fs.rmSync(dashboardBundleDir, { recursive: true, force: true });
        fs.mkdirSync(dashboardBundleDir, { recursive: true });
        copyDirContents(dashboardRestSrcDir, dashboardBundleDir);
        fs.cpSync(cdssSrcDir, path.join(dashboardBundleDir, 'cdss'), { recursive: true });

        const { execSync } = require('child_process');
        execSync(
            'pip install psycopg2-binary --target ' + dashboardBundleDir +
            ' --platform manylinux2014_x86_64 --implementation cp --python-version 3.11 --only-binary=:all: --quiet',
            { stdio: 'inherit' }
        );

        const dashboardFn = new lambda.Function(this, 'DashboardFunction', {
            runtime: lambda.Runtime.PYTHON_3_11,
            handler: 'dashboard_handler.lambda_handler',
            code: lambda.Code.fromAsset(dashboardBundleDir),
            vpc,
            vpcSubnets: { subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS },
            securityGroups: [lambdaSecurityGroup],
            environment: {
                ...dbEnv,
            },
            layers: [sharedLayer],
            timeout: cdk.Duration.seconds(30),
        });

        cluster.grantConnect(dashboardFn, rdsSecret.secretValueFromJson('username').toString());
        rdsSecret.grantRead(dashboardFn);

        // ----------------------------------------------------------------
        // 12. REST API Gateway
        // ----------------------------------------------------------------
        const api = new apigateway.RestApi(this, 'CdssRestApi', {
            restApiName: `CDSS Clinical API-${envName.valueAsString}`,
            defaultCorsPreflightOptions: {
                allowOrigins: apigateway.Cors.ALL_ORIGINS,
                allowMethods: apigateway.Cors.ALL_METHODS,
            },
        });

        // POST /agent  — supervisor entry point
        api.root.addResource('agent').addMethod('POST', new apigateway.LambdaIntegration(supervisorAgent));

        // GET /dashboard
        api.root.addResource('dashboard').addMethod('GET', new apigateway.LambdaIntegration(dashboardFn));

        // GET /health  — routes to dashboardFn which should call SELECT 1
        api.root.addResource('health').addMethod('GET', new apigateway.LambdaIntegration(dashboardFn));

        const apiRoot = api.root.addResource('api');
        const apiV1 = apiRoot.addResource('v1');

        // POST /api/ai/summarize
        const ai = apiRoot.addResource('ai');
        ai.addResource('summarize').addMethod('POST', new apigateway.LambdaIntegration(dashboardFn));

        // POST /api/v1/ai/summarize
        const aiV1 = apiV1.addResource('ai');
        aiV1.addResource('summarize').addMethod('POST', new apigateway.LambdaIntegration(dashboardFn));

        const patients = apiV1.addResource('patients');
        patients.addMethod('GET', new apigateway.LambdaIntegration(dashboardFn));
        patients.addMethod('POST', new apigateway.LambdaIntegration(dashboardFn));
        const patientById = patients.addResource('{id}');
        patientById.addMethod('GET', new apigateway.LambdaIntegration(dashboardFn));
        patientById.addMethod('PUT', new apigateway.LambdaIntegration(dashboardFn));

        const surgeries = apiV1.addResource('surgeries');
        surgeries.addMethod('GET', new apigateway.LambdaIntegration(dashboardFn));
        const surgeryById = surgeries.addResource('{id}');
        surgeryById.addMethod('GET', new apigateway.LambdaIntegration(dashboardFn));
        surgeryById.addResource('analyse').addMethod('POST', new apigateway.LambdaIntegration(dashboardFn));

        const appointments = apiV1.addResource('appointments');
        appointments.addMethod('GET', new apigateway.LambdaIntegration(dashboardFn));
        appointments.addMethod('POST', new apigateway.LambdaIntegration(dashboardFn));

        const medications = apiV1.addResource('medications');
        medications.addMethod('GET', new apigateway.LambdaIntegration(dashboardFn));
        medications.addMethod('POST', new apigateway.LambdaIntegration(dashboardFn));

        apiV1.addResource('schedule').addMethod('GET', new apigateway.LambdaIntegration(dashboardFn));

        apiV1.addResource('resources').addMethod('GET', new apigateway.LambdaIntegration(dashboardFn));

        const consultations = apiV1.addResource('consultations');
        consultations.addMethod('GET', new apigateway.LambdaIntegration(dashboardFn));
        consultations.addMethod('POST', new apigateway.LambdaIntegration(dashboardFn));
        consultations.addResource('start').addMethod('POST', new apigateway.LambdaIntegration(dashboardFn));

        // GET /api/v1/tasks
        apiV1.addResource('tasks').addMethod('GET', new apigateway.LambdaIntegration(dashboardFn));

        // POST /api/v1/activity
        apiV1.addResource('activity').addMethod('POST', new apigateway.LambdaIntegration(dashboardFn));

        // ----------------------------------------------------------------
        // 13. CloudFormation Outputs
        // ----------------------------------------------------------------
        new cdk.CfnOutput(this, 'RestApiUrl', {
            value: api.url,
            description: 'API Gateway base URL',
        });

        new cdk.CfnOutput(this, 'RdsConfigSecretName', {
            value: rdsSecret.secretName,
            description: 'Value to use as RDS_CONFIG_SECRET_NAME in all Lambdas and local .env files',
        });

        new cdk.CfnOutput(this, 'RdsClusterEndpoint', {
            value: cluster.clusterEndpoint.hostname,
            description: 'Aurora cluster endpoint (useful for SSM tunnel setup)',
        });
    }
}
