---
name: eks
description: AWS EKS-specific concerns — IRSA, managed node groups vs. Karpenter/Fargate, VPC CNI IP planning, and the AWS Load Balancer Controller. Use alongside the kubernetes skill when the target cluster is EKS.
---

# EKS (Amazon Elastic Kubernetes Service)

EKS-specific delta on top of the `kubernetes` core skill.

## Identity: IRSA / Pod Identity

- IAM Roles for Service Accounts (IRSA) or the newer EKS Pod Identity — pods assume an IAM role via their
  ServiceAccount, no static AWS credentials in the pod.
- Check: ServiceAccount has the `eks.amazonaws.com/role-arn` annotation (IRSA) or a Pod Identity
  association exists; the IAM role's trust policy is scoped to the specific OIDC provider + namespace +
  ServiceAccount, not open to any pod in the cluster.

## Compute

- Managed node groups: AWS manages the underlying EC2 lifecycle; still need a scaling mechanism
  (Cluster Autoscaler or Karpenter) layered on top.
- Karpenter: faster, more flexible bin-packing and just-in-time node provisioning — increasingly the
  default recommendation over Cluster Autoscaler for new clusters, but confirm the team's operational
  familiarity before introducing it.
- Fargate profiles: no node management at all, per-pod billing — good fit for bursty/low-density
  workloads, not for workloads needing DaemonSets, privileged access, or GPU.

## Networking

- VPC CNI assigns pods real VPC IPs by default — plan subnet CIDR size for pod density, not just node
  count; IP exhaustion on the VPC CNI is a common EKS-specific outage cause. Consider
  `ENABLE_PREFIX_DELEGATION` or custom networking (secondary CIDR) for higher pod density per node.
- AWS Load Balancer Controller manages ALB/NLB from Ingress/Service annotations — confirm it's installed
  before assuming `kubernetes.io/ingress.class: alb` annotations will do anything.
- Security groups for pods (via the VPC CNI) is an alternative to NetworkPolicies for AWS-native network
  segmentation — know which one the cluster actually uses before writing policy.

## Key Commands

```bash
aws eks update-kubeconfig --name <cluster> --region <region>
aws eks describe-cluster --name <cluster>
kubectl get pods -n kube-system -l k8s-app=aws-node    # VPC CNI pods
eksctl get iamidentitymapping --cluster <cluster>       # aws-auth mapping, if using eksctl-managed access
```

## Common Pitfalls

- IRSA role trust policy scoped to the OIDC provider but not to a specific namespace/ServiceAccount
  condition — any pod in the cluster with a matching ServiceAccount name in any namespace can assume it.
- Node group AMI/Kubernetes version drifting behind the control plane's version, risking incompatibility
  on the next control-plane upgrade.
- Pod IP exhaustion on a subnet sized for node count, not pod count, causing pods to stay `Pending` with
  no obvious resource-pressure explanation until you check ENI/IP availability specifically.
