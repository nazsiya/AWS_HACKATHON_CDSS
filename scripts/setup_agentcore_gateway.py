#!/usr/bin/env python3
"""
Setup Bedrock AgentCore Gateway and add CDSS Gateway Tools Lambda as target.

Usage:
  python scripts/setup_agentcore_gateway.py [LAMBDA_ARN]
  GATEWAY_GET_HOSPITALS_LAMBDA_ARN=arn:aws:lambda:... python scripts/setup_agentcore_gateway.py

  From project root (D:\\AI_Hackathon_CDSS), not from infrastructure/:
    cd D:\\AI_Hackathon_CDSS
    python scripts/setup_agentcore_gateway.py <LAMBDA_ARN>

  PowerShell (from project root, get ARN from Terraform). Use two lines—do not pass a parenthesized expression as the script argument:
    $arn = (cd infrastructure; terraform output -raw gateway_get_hospitals_lambda_arn)
    python scripts/setup_agentcore_gateway.py $arn

Prerequisites:
  - Terraform apply completed (gateway_tools Lambda deployed)
  - pip install boto3
  - AWS credentials configured. Gateway is created in the **same region as the Lambda** (from ARN); for CDSS in ap-south-1 do not set AWS_REGION so the script uses the Lambda's region. To force a different gateway region (e.g. us-east-1 if AgentCore is not in ap-south-1), set AGENTCORE_GATEWAY_REGION.

Output:
  - gateway_config.json with gateway_url, gateway_id, region, client_info (for NONE auth client_info may be empty)

See docs/agentcore-gateway-manual-steps.md and docs/agentcore-next-steps-implementation.md.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def get_lambda_arn() -> str:
    arn = os.environ.get("GATEWAY_GET_HOSPITALS_LAMBDA_ARN", "").strip()
    if not arn and len(sys.argv) > 1:
        arn = sys.argv[1].strip()
    if not arn or not arn.startswith("arn:aws:lambda:"):
        print("Usage: python scripts/setup_agentcore_gateway.py <LAMBDA_ARN>", file=sys.stderr)
        print("   or: GATEWAY_GET_HOSPITALS_LAMBDA_ARN=arn:aws:lambda:... python scripts/setup_agentcore_gateway.py", file=sys.stderr)
        print("Get LAMBDA_ARN from: cd infrastructure && terraform output -raw gateway_get_hospitals_lambda_arn", file=sys.stderr)
        sys.exit(1)
    return arn


def _region_from_lambda_arn(arn: str) -> str:
    """Parse region from arn:aws:lambda:REGION:account:function:name."""
    parts = arn.split(":")
    if len(parts) >= 4:
        return parts[3]  # region
    return "ap-south-1"


def main() -> None:
    lambda_arn = get_lambda_arn()
    # Gateway in same region as Lambda (ap-south-1 for CDSS). Ignore AWS_REGION so shell default doesn't force us-east-1.
    region = os.environ.get("AGENTCORE_GATEWAY_REGION") or _region_from_lambda_arn(lambda_arn)

    try:
        import boto3
    except ImportError:
        print("Install boto3: pip install boto3", file=sys.stderr)
        sys.exit(1)

    # AgentCore Control Plane client (gateway creation)
    try:
        client = boto3.client("bedrock-agentcore-control", region_name=region)
    except Exception as e:
        print(
            f"bedrock-agentcore-control not available in {region} or credentials missing: {e}",
            file=sys.stderr,
        )
        print(
            "Create Gateway manually per docs/agentcore-gateway-manual-steps.md and AWS Console.",
            file=sys.stderr,
        )
        _write_config_placeholder(region)
        sys.exit(1)

    gateway_name = f"cdss-gateway-{region}"
    role_name = f"cdss-agentcore-gateway-role-{region.replace('-', '_')}"

    # 1) Ensure Gateway service role exists (gateway assumes this to invoke Lambda)
    iam = boto3.client("iam", region_name=region)
    account_id = boto3.client("sts").get_caller_identity()["Account"]
    role_arn = f"arn:aws:iam::{account_id}:role/{role_name}"

    try:
        iam.get_role(RoleName=role_name)
    except iam.exceptions.NoSuchEntityException:
        trust = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"Service": "bedrock-agentcore.amazonaws.com"},
                    "Action": "sts:AssumeRole",
                }
            ],
        }
        iam.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(trust),
            Description="AgentCore Gateway execution role for CDSS",
        )
        policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": ["lambda:InvokeFunction"],
                    "Resource": [lambda_arn],
                }
            ],
        }
        iam.put_role_policy(
            RoleName=role_name,
            PolicyName="invoke-gateway-tools-lambda",
            PolicyDocument=json.dumps(policy),
        )
        print(f"Created IAM role {role_arn}")

    # 2) Create Gateway (authorizerType NONE for simplest setup)
    try:
        gw = client.create_gateway(
            name=gateway_name,
            roleArn=role_arn,
            protocolType="MCP",
            authorizerType="NONE",
            description="CDSS AgentCore Gateway (get_hospitals, get_ot_status, get_abdm_record)",
        )
        gateway_id = gw.get("gatewayId") or gw.get("gatewayIdentifier", "")
        gateway_arn = gw.get("gatewayArn", "")
        if not gateway_id:
            gateway_id = gateway_arn.split("/")[-1] if gateway_arn else ""
        print(f"Created Gateway: {gateway_id} ({gateway_arn})")
    except client.exceptions.ConflictException:
        # Gateway with same name already exists; list and reuse it
        list_gw = client.list_gateways()
        summaries = list_gw.get("gatewaySummaries") or list_gw.get("gateways") or list_gw.get("items") or []
        gateway_id = ""
        gateway_arn = ""
        for g in summaries:
            name = g.get("name") or g.get("gatewayName") or ""
            gid = g.get("gatewayId") or g.get("gatewayIdentifier") or g.get("id") or ""
            garn = g.get("gatewayArn") or g.get("arn") or ""
            if name == gateway_name or gateway_name in name or (gid and gateway_name in gid):
                gateway_id = gid
                gateway_arn = garn
                break
        if not gateway_id and summaries:
            # Use first gateway if name match failed (API may use different name format)
            g = summaries[0]
            gateway_id = g.get("gatewayId") or g.get("gatewayIdentifier") or g.get("id") or ""
            gateway_arn = g.get("gatewayArn") or g.get("arn") or ""
        if gateway_id:
            print(f"Using existing Gateway: {gateway_id}")
        else:
            print("Gateway name conflict; use a different name or delete existing gateway.", file=sys.stderr)
            sys.exit(1)
    except Exception as e:
        print(f"CreateGateway failed: {e}", file=sys.stderr)
        _write_config_placeholder(region)
        sys.exit(1)

    # Ensure we have a valid gateway_arn for AddPermission (list_gateways may not return it)
    if not gateway_arn and gateway_id and account_id:
        gateway_arn = f"arn:aws:bedrock-agentcore:{region}:{account_id}:gateway/{gateway_id}"

    # 3) Create target for the gateway
    # Control Plane API only accepts targetConfiguration.mcp (not Lambda). Add Lambda target in Console.
    target_name = "get-hospitals-target"
    print(
        "CreateGatewayTarget API supports only MCP targets. Add your Lambda as a target in Console:",
    )
    print("  Bedrock > AgentCore > Gateways >", gateway_id, "> Targets > Add target.")

    # 4) Lambda permission for Gateway – use Lambda's region (Gateway may be in us-east-1, Lambda in ap-south-1)
    lambda_region = _region_from_lambda_arn(lambda_arn)
    lambda_client = boto3.client("lambda", region_name=lambda_region)
    try:
        lambda_client.add_permission(
            FunctionName=lambda_arn,
            StatementId="AllowAgentCoreGatewayInvoke",
            Action="lambda:InvokeFunction",
            Principal="bedrock-agentcore.amazonaws.com",
            SourceArn=gateway_arn,
        )
        print("Added Lambda permission for Gateway.")
    except lambda_client.exceptions.ResourceConflictException:
        print("Lambda permission already exists; skipping.")
    except Exception as e:
        print(f"Lambda AddPermission failed (non-fatal): {e}", file=sys.stderr)

    # 5) Gateway invoke URL (data plane); format per AWS docs
    gateway_url = f"https://gateway.bedrock-agentcore.{region}.amazonaws.com/gateways/{gateway_id}"
    config = {
        "gateway_url": gateway_url,
        "gateway_id": gateway_id,
        "gateway_arn": gateway_arn,
        "region": region,
        "target_name": target_name,
        "client_info": {},
    }
    out_path = Path(__file__).resolve().parent.parent / "gateway_config.json"
    with open(out_path, "w") as f:
        json.dump(config, f, indent=2)
    print(f"Wrote {out_path}")
    print("Tool name format: {target_name}___get_hospitals  e.g. get-hospitals-target___get_hospitals")


def _write_config_placeholder(region: str) -> None:
    out_path = Path(__file__).resolve().parent.parent / "gateway_config.json"
    config = {
        "gateway_url": "",
        "gateway_id": "",
        "gateway_arn": "",
        "region": region,
        "target_name": "get-hospitals-target",
        "client_info": {},
        "_comment": "Fill gateway_url and gateway_id after creating Gateway manually (see docs/agentcore-gateway-manual-steps.md)",
    }
    with open(out_path, "w") as f:
        json.dump(config, f, indent=2)
    print(f"Wrote placeholder {out_path}")


if __name__ == "__main__":
    main()
