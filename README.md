# Automated Incident Remediation with AWS DevOps Agent and Kiro CLI

Closed-loop incident remediation for AWS workloads. When AWS DevOps Agent completes a mitigation analysis, an event-driven bridge routes the findings to Kiro CLI running in headless mode on CodeBuild. Kiro CLI applies the fix to your codebase and creates a pull request for human review.

```
CloudWatch alarm → DevOps Agent investigates → Mitigation plan
    → EventBridge → Lambda (extract) → SQS → Lambda (trigger)
    → CodeBuild (Kiro CLI) → Feature branch + PR
    → Human reviews → Merge → Fix deployed
```

## Repository Structure

```
infra/
  app-template.yaml            # Sample application (VPC, ALB, EC2, RDS)
  event-capture-template.yaml  # Captures DevOps Agent mitigation events → SQS
  remediation-template.yaml    # CodeBuild project + Lambda SQS trigger
  nginx.conf                   # Nginx reverse proxy config

backend/                       # Python Flask API
frontend/                      # React + Vite SPA
bridge/
  prompt_generator.py          # Converts mitigation payload → Kiro CLI prompt
scripts/
  populate_data.py             # Seeds test data into the sample app
  trigger_high_cpu.py          # Simulates high CPU load

buildspec.yml                  # CodeBuild buildspec for Kiro CLI remediation
.kiro/steering/
  remediation-agent.md         # Steering file that guides Kiro CLI behavior
```

## Prerequisites

- An **AWS account** with an eligible [AWS Support plan](https://aws.amazon.com/premiumsupport/) for AWS DevOps Agent access
- An **AWS DevOps Agent space** configured with access to your account's CloudWatch, CloudTrail, and CodeCommit
- **Kiro CLI** with a Pro, Pro+, or Power subscription (required for [headless mode API keys](https://kiro.dev/docs/cli/headless/))
- **AWS CLI** configured with appropriate credentials
- **Git** configured with CodeCommit credential helper
- **Python 3.12+** and **Node.js 20+**

## Deployment

There are three CloudFormation stacks to deploy, plus a prerequisite DevOps Agent setup.

### Step 0: Set up AWS DevOps Agent

Create an Agent Space and onboard your AWS account following the [DevOps Agent Getting Started Guide](https://docs.aws.amazon.com/devopsagent/latest/userguide/). When configuring the Agent Space, scope it to resources tagged with `Project: BlogPortal` — this is the tag applied to all resources created by the sample application stack. Ensure the space has access to CloudWatch, CloudTrail, and CodeCommit for the account where you'll deploy the sample app. For detailed configuration and production best practices, see [Leverage Agentic AI for Autonomous Incident Response with AWS DevOps Agent](https://aws.amazon.com/blogs/devops/leverage-agentic-ai-for-autonomous-incident-response-with-aws-devops-agent/).

In this walkthrough, you'll trigger investigations manually from the DevOps Agent chat interface. To automate investigation triggers from CloudWatch Alarms, see [How to automatically trigger AWS DevOps Agent investigations from CloudWatch Alarms](https://repost.aws/articles/ARCIbpJr1MSuunMLBgeihmNg).

### Step 1: Deploy the sample application

```bash
aws cloudformation deploy \
  --template-file infra/app-template.yaml \
  --stack-name devops-agent-sample-app \
  --parameter-overrides \
    DBMasterPassword=<YOUR_DB_PASSWORD> \
    DBMasterUsername=<YOUR_DB_USERNAME> \
    AdminPassword=<YOUR_ADMIN_PASSWORD> \
    RepoUrl=<YOUR_CODECOMMIT_REPO_HTTPS_URL> \
  --capabilities CAPABILITY_IAM \
  --region us-east-1
```

This creates a VPC, ALB, EC2 instance (Flask + Nginx), and RDS MySQL database.

### Step 2: Create the Lambda layer and deploy the event capture stack

The Lambda runtime's bundled boto3 doesn't include the `devops-agent` service. Create a layer with a newer version:

```bash
mkdir -p /tmp/boto3-layer/python
pip3 install boto3 -t /tmp/boto3-layer/python --quiet
cd /tmp/boto3-layer && zip -r /tmp/boto3-layer.zip python -q

LAYER_ARN=$(aws lambda publish-layer-version \
  --layer-name boto3-devops-agent \
  --description "boto3 with devops-agent service support" \
  --zip-file fileb:///tmp/boto3-layer.zip \
  --compatible-runtimes python3.12 \
  --region us-east-1 \
  --query 'LayerVersionArn' \
  --output text)

echo "Layer ARN: $LAYER_ARN"
```

Deploy the event capture stack:

```bash
aws cloudformation deploy \
  --template-file infra/event-capture-template.yaml \
  --stack-name devops-agent-kiro-bridge \
  --parameter-overrides Boto3LayerArn=$LAYER_ARN \
  --capabilities CAPABILITY_IAM \
  --region us-east-1
```

This creates an EventBridge rule (captures `Mitigation Completed` events), a Lambda function (extracts mitigation data via the DevOps Agent API), an SQS queue, and a dead-letter queue.

### Step 3: Store the Kiro API key and deploy the remediation stack

Generate an API key from the [Kiro portal](https://app.kiro.dev/) and store it in Secrets Manager:

```bash
aws secretsmanager create-secret \
  --name devops-agent-kiro-bridge/kiro-api-key \
  --secret-string "<YOUR_KIRO_API_KEY>" \
  --region us-east-1
```

Deploy the remediation stack:

```bash
aws cloudformation deploy \
  --template-file infra/remediation-template.yaml \
  --stack-name devops-agent-kiro-pipeline \
  --parameter-overrides RepositoryName=<YOUR_CODECOMMIT_REPO_NAME> \
  --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM \
  --region us-east-1
```

This creates a CodeBuild project (runs Kiro CLI in headless mode) and a Lambda function that triggers CodeBuild when messages arrive in the SQS queue.

## How It Works

1. Your application experiences an issue. CloudWatch alarms fire.
2. AWS DevOps Agent investigates, identifies root cause, and generates a mitigation plan.
3. An EventBridge rule captures the `Mitigation Completed` event and invokes a Lambda function.
4. The Lambda extracts the mitigation summary and execution plan from the DevOps Agent API and publishes to SQS.
5. A trigger Lambda starts a CodeBuild project, passing the SQS message as an environment variable.
6. CodeBuild installs Kiro CLI, generates a remediation prompt from the mitigation payload, and runs `kiro-cli chat --no-interactive --trust-tools=read,write,grep,shell`.
7. Kiro CLI, guided by the steering file, modifies the CloudFormation template or application code.
8. Guardrails validate the changes (file count, protected files, syntax checks).
9. CodeBuild commits to a feature branch, pushes, and creates a CodeCommit pull request.
10. A developer reviews and approves the PR.

## Testing

Send a test message to the SQS queue to trigger the full flow:

```bash
QUEUE_URL=$(aws cloudformation describe-stacks \
  --stack-name devops-agent-kiro-bridge \
  --query 'Stacks[0].Outputs[?OutputKey==`RemediationQueueUrl`].OutputValue' \
  --output text --region us-east-1)

aws sqs send-message \
  --queue-url "$QUEUE_URL" \
  --message-body '{
    "agent_space_id": "test-1234-5678",
    "execution_id": "test-exec-001",
    "mitigation_summary": {
      "action": "Upgrade EC2 instance type from t2.micro to t3.small",
      "reasoning": "High CPU utilization causing request timeouts"
    },
    "execution_plan": [{
      "step": "apply",
      "instructions": [{
        "instruction": {
          "type": "command",
          "content": "Modify InstanceType parameter in CloudFormation template"
        },
        "reasoning": {
          "purpose": "Right-size compute for current traffic",
          "risks": [],
          "advisory": []
        }
      }]
    }]
  }' \
  --region us-east-1
```

Monitor the CodeBuild job in the console or via:

```bash
aws codebuild list-builds-for-project \
  --project-name devops-agent-kiro-pipeline-KiroRemediation \
  --region us-east-1
```

To generate real incidents against the sample application, use the trigger scripts after populating test data:

```bash
# Install the requests library (needed by all scripts)
pip3 install requests

# Populate test data (run from your local machine with ALB URL)
python3 scripts/populate_data.py --url http://<ALB_DNS_NAME> --password <YOUR_ADMIN_PASSWORD>

# Trigger high CPU (causes CloudWatch CPU alarm)
python3 scripts/trigger_high_cpu.py --url http://<ALB_DNS_NAME> --password <YOUR_ADMIN_PASSWORD>
```

## Guardrails

The solution includes two layers of protection to keep Kiro CLI focused:

**Steering file** (`kiro/steering/remediation-agent.md`):
- Defines which files Kiro CLI can modify and which are protected
- Limits scope to maximum 3 files per remediation
- Prevents creating new files, installing dependencies, or deleting files
- Blocks internet access and broad refactoring

**Buildspec validation** (`buildspec.yml`):
- Aborts if more than 5 files were changed
- Aborts if protected files (buildspec, infra templates, bridge code) were modified
- Runs `py_compile` on changed Python files
- Validates YAML syntax on changed templates
- CodeBuild timeout set to 15 minutes

## Cleanup

Remove all resources in reverse order:

```bash
# 1. Delete the remediation stack
aws cloudformation delete-stack --stack-name devops-agent-kiro-pipeline --region us-east-1

# 2. Delete the event capture stack
aws cloudformation delete-stack --stack-name devops-agent-kiro-bridge --region us-east-1

# 3. Delete the sample application stack
aws cloudformation delete-stack --stack-name devops-agent-sample-app --region us-east-1

# 4. Delete the Kiro API key secret
aws secretsmanager delete-secret \
  --secret-id devops-agent-kiro-bridge/kiro-api-key \
  --force-delete-without-recovery \
  --region us-east-1

# 5. Delete the Lambda layer
aws lambda delete-layer-version \
  --layer-name boto3-devops-agent \
  --version-number 1 \
  --region us-east-1
```

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Lambda: `UnknownServiceError: 'devops-agent'` | Lambda layer is missing or wrong version. Rebuild and redeploy the boto3 layer. |
| Lambda: `No mitigation execution found` | The task may not have a mitigation execution yet. Check `list_executions` output in CloudWatch logs. |
| Lambda: `No mitigation data found` | Journal records may use a different structure. Check CloudWatch logs for the raw API response. |
| CodeBuild: `kiro-cli not found in PATH` | The install script may have failed. Check the INSTALL phase logs. |
| CodeBuild: `GUARDRAIL: Too many files changed` | Kiro CLI modified more than 5 files. Review the steering file constraints. |
| CodeBuild: `GUARDRAIL: Protected file was modified` | Kiro CLI tried to modify a protected file. The steering file should prevent this. |
| CodeBuild: CodeCommit push fails | Check that the CodeBuild IAM role has `codecommit:GitPush` permission. |
| CodeBuild: PR creation fails | Check that the CodeBuild IAM role has `codecommit:CreatePullRequest` permission. |
| CodeBuild: Kiro CLI tries to open browser | `KIRO_API_KEY` is not set. Verify the Secrets Manager secret exists and the CodeBuild role has `secretsmanager:GetSecretValue` permission. |

## Related Resources

- [AWS DevOps Agent documentation](https://docs.aws.amazon.com/devopsagent/latest/userguide/)
- [Kiro CLI headless mode](https://kiro.dev/docs/cli/headless/)
- [Kiro CLI steering files](https://kiro.dev/docs/cli/steering/)
- [Amazon EventBridge](https://docs.aws.amazon.com/eventbridge/latest/userguide/)

## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This library is licensed under the MIT-0 License. See the LICENSE file.
