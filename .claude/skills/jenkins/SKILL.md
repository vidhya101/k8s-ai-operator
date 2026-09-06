---
name: jenkins
description: Author and review Jenkins declarative pipelines — Jenkinsfile structure, credentials binding, and agent/executor design. Use when the CI/CD system is Jenkins rather than GitHub Actions.
---

# Jenkins

Reference for repos using Jenkins (`Jenkinsfile`) instead of, or alongside, GitHub Actions.

## Declarative Pipeline Shape

```groovy
pipeline {
  agent { label 'docker' }
  options {
    timeout(time: 30, unit: 'MINUTES')
    disableConcurrentBuilds()
  }
  environment {
    IMAGE = "registry.example.com/app:${env.GIT_COMMIT}"
  }
  stages {
    stage('Test') {
      steps { sh 'npm ci && npm test' }
    }
    stage('Build') {
      steps { sh "docker build -t ${IMAGE} ." }
    }
    stage('Scan') {
      steps { sh "trivy image --exit-code 1 --severity HIGH,CRITICAL ${IMAGE}" }
    }
    stage('Push') {
      when { branch 'main' }
      steps {
        withCredentials([usernamePassword(credentialsId: 'registry-creds',
                          usernameVariable: 'U', passwordVariable: 'P')]) {
          sh "echo \$P | docker login registry.example.com -u \$U --password-stdin"
          sh "docker push ${IMAGE}"
        }
      }
    }
  }
}
```

## Core Principles

- Declarative pipeline over Scripted where possible — more restricted syntax, easier to review, harder to
  accidentally write something unsafe.
- Credentials via the Jenkins Credentials store + `withCredentials`, never hardcoded in the Jenkinsfile or
  echoed to console output.
- `when { branch 'main' }` (or equivalent) gating any deploy/push stage — mirror the PR-vs-merge separation
  used in the `github-actions` skill.
- Ephemeral agents (Kubernetes pod templates, Docker-in-Docker agents spun up per build) over static
  long-lived build agents where possible, for the same state-leakage reasons as GitHub Actions runners.

## Key Commands / Checks

```bash
jenkins-cli build <job> -f            # trigger a build, follow logs
jenkins-cli console <job> <build-#>   # fetch console output for a specific build
# Or via REST API:
curl -s "<jenkins-url>/job/<job>/lastBuild/api/json"
```

## Common Pitfalls

- Secrets passed as plain environment variables instead of `withCredentials`, ending up in build logs or
  `env` dumps.
- Shared static agents accumulating leftover workspace state/credentials between unrelated jobs.
- No `timeout`/`disableConcurrentBuilds`, letting a stuck build hold an agent indefinitely or race with a
  concurrent run of the same pipeline against the same environment.
- Groovy sandbox escapes or unreviewed shared-library changes running with more trust than the actual
  pipeline code gets — review shared libraries with the same scrutiny as the Jenkinsfile itself.
