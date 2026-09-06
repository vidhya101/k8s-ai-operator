IMG ?= appworkload-operator:dev

.PHONY: build test vet fmt run docker-build install uninstall deploy undeploy

build: ## Compile the manager binary.
	go build -o bin/manager .

test: ## Run unit tests.
	go test ./... -race -coverprofile=coverage.out

vet: ## Static analysis.
	go vet ./...

fmt:
	gofmt -l -w .

run: ## Run the operator against whatever cluster is in your current kubeconfig context.
	go run .

docker-build:
	docker build -t $(IMG) .

install: ## Install just the CRD.
	kubectl apply -f config/crd/bases/platform.io_appworkloads.yaml

uninstall:
	kubectl delete -f config/crd/bases/platform.io_appworkloads.yaml --ignore-not-found

deploy: ## Install the whole operator (namespace + CRD + RBAC + manager Deployment).
	kustomize build config/default | kubectl apply -f -

undeploy:
	kustomize build config/default | kubectl delete -f - --ignore-not-found

# `controller-gen` (kubebuilder's code/manifest generator) isn't vendored into this repo — install
# it locally if you'd rather regenerate api/v1alpha1/zz_generated.deepcopy.go and the CRD YAML
# from the +kubebuilder markers than maintain the hand-written equivalents in this repo:
#   go install sigs.k8s.io/controller-tools/cmd/controller-gen@latest
generate:
	controller-gen object:headerFile="hack/boilerplate.go.txt" paths="./..."

manifests:
	controller-gen crd rbac:roleName=appworkload-operator-manager-role paths="./..." output:crd:artifacts:config=config/crd/bases
