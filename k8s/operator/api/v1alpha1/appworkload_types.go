package v1alpha1

import (
	corev1 "k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime"
)

// AppWorkloadSpec is intentionally cloud- and language-agnostic: it describes *what* to run
// (an already-built, already-scanned, already-signed image — the CI pipeline in
// .github/workflows/reusable-ci-cd.yml is what produced it) and *how much of it*, never *how*
// to build it. Cloud-specific identity binding (IRSA/Workload Identity/AAD) is passed in as
// plain annotations by whichever overlay/caller creates the CR — the controller never branches
// on cloud provider itself.
type AppWorkloadSpec struct {
	// Image is the fully-qualified, digest-pinned image reference to run.
	// +kubebuilder:validation:Required
	// +kubebuilder:validation:MinLength=1
	Image string `json:"image"`

	// Port the container listens on.
	// +kubebuilder:default=8080
	Port int32 `json:"port,omitempty"`

	// Replicas is the starting/fixed replica count. Ignored once the HPA has taken over scaling
	// (MinReplicas/MaxReplicas set) beyond the very first reconcile.
	// +kubebuilder:default=2
	// +kubebuilder:validation:Minimum=1
	Replicas *int32 `json:"replicas,omitempty"`

	// MinReplicas/MaxReplicas enable a HorizontalPodAutoscaler when both are set.
	// +optional
	MinReplicas *int32 `json:"minReplicas,omitempty"`
	// +optional
	MaxReplicas *int32 `json:"maxReplicas,omitempty"`

	// TargetCPUUtilizationPercentage is the HPA's CPU target. Only used when MinReplicas/MaxReplicas are set.
	// +kubebuilder:default=70
	TargetCPUUtilizationPercentage *int32 `json:"targetCPUUtilizationPercentage,omitempty"`

	// Resources are the container's requests/limits. A missing value is filled from the
	// namespace's LimitRange (see k8s/app/base/limitrange.yaml) — the operator does not invent
	// its own defaults on top of the cluster's.
	// +optional
	Resources corev1.ResourceRequirements `json:"resources,omitempty"`

	// Env is passed straight through to the container. For secrets, reference a Secret key
	// (corev1.EnvVarSource.SecretKeyRef) — never put a literal secret value in an AppWorkload CR,
	// which (like any CR) is readable by anyone with get/list on this resource type.
	// +optional
	Env []corev1.EnvVar `json:"env,omitempty"`

	// ServiceAccountAnnotations lets the caller attach cloud workload-identity binding
	// (eks.amazonaws.com/role-arn | iam.gke.io/gcp-service-account | azure.workload.identity/client-id)
	// without the controller needing to know which cloud it's running on.
	// +optional
	ServiceAccountAnnotations map[string]string `json:"serviceAccountAnnotations,omitempty"`

	// LivenessPath/ReadinessPath are the HTTP health endpoints the app exposes.
	// +kubebuilder:default=/healthz
	LivenessPath string `json:"livenessPath,omitempty"`
	// +kubebuilder:default=/readyz
	ReadinessPath string `json:"readinessPath,omitempty"`

	// MinAvailable feeds the PodDisruptionBudget. Defaults to 1 when unset and Replicas > 1.
	// +optional
	MinAvailable *int32 `json:"minAvailable,omitempty"`

	// Cloud is a free-text, informational label only (aws|gcp|azure|local|...) — surfaced on the
	// generated objects' labels for observability/cost-attribution tooling. The controller's
	// reconcile logic never branches on this field.
	// +optional
	Cloud string `json:"cloud,omitempty"`
}

// AppWorkloadStatus surfaces just enough for `kubectl get appworkload` / GitOps health checks to
// mean something, without duplicating everything the Deployment/HPA already report.
type AppWorkloadStatus struct {
	// ObservedGeneration lets a caller tell "status is stale" from "status is current".
	ObservedGeneration int64 `json:"observedGeneration,omitempty"`

	// ReadyReplicas mirrors the managed Deployment's status.readyReplicas.
	ReadyReplicas int32 `json:"readyReplicas,omitempty"`

	// Conditions follow the standard Kubernetes condition convention (type/status/reason/message).
	// +optional
	// +patchMergeKey=type
	// +patchStrategy=merge
	Conditions []metav1.Condition `json:"conditions,omitempty" patchStrategy:"merge" patchMergeKey:"type"`
}

// +kubebuilder:object:root=true
// +kubebuilder:subresource:status
// +kubebuilder:printcolumn:name="Image",type=string,JSONPath=`.spec.image`
// +kubebuilder:printcolumn:name="Ready",type=integer,JSONPath=`.status.readyReplicas`
// +kubebuilder:printcolumn:name="Cloud",type=string,JSONPath=`.spec.cloud`
// +kubebuilder:printcolumn:name="Age",type=date,JSONPath=`.metadata.creationTimestamp`

// AppWorkload is the operator's single custom resource: one CR per deployable application,
// portable across AWS/GCP/Azure/on-prem/local — see k8s/operator/config/samples for an example.
type AppWorkload struct {
	metav1.TypeMeta   `json:",inline"`
	metav1.ObjectMeta `json:"metadata,omitempty"`

	Spec   AppWorkloadSpec   `json:"spec,omitempty"`
	Status AppWorkloadStatus `json:"status,omitempty"`
}

// +kubebuilder:object:root=true

// AppWorkloadList contains a list of AppWorkload.
type AppWorkloadList struct {
	metav1.TypeMeta `json:",inline"`
	metav1.ListMeta `json:"metadata,omitempty"`
	Items           []AppWorkload `json:"items"`
}

// ---------------------------------------------------------------------------------------------
// DeepCopy implementations. Normally produced by `controller-gen object:headerFile=...` — hand
// written here since this repo doesn't invoke the code-generator toolchain in CI. Regenerate with
// `make generate` (see the Makefile) if controller-gen is available and you'd rather not maintain
// these by hand going forward; the shape below is exactly what it would emit for this API.
// ---------------------------------------------------------------------------------------------

func (in *AppWorkloadSpec) DeepCopyInto(out *AppWorkloadSpec) {
	*out = *in
	if in.Replicas != nil {
		out.Replicas = new(int32)
		*out.Replicas = *in.Replicas
	}
	if in.MinReplicas != nil {
		out.MinReplicas = new(int32)
		*out.MinReplicas = *in.MinReplicas
	}
	if in.MaxReplicas != nil {
		out.MaxReplicas = new(int32)
		*out.MaxReplicas = *in.MaxReplicas
	}
	if in.TargetCPUUtilizationPercentage != nil {
		out.TargetCPUUtilizationPercentage = new(int32)
		*out.TargetCPUUtilizationPercentage = *in.TargetCPUUtilizationPercentage
	}
	if in.MinAvailable != nil {
		out.MinAvailable = new(int32)
		*out.MinAvailable = *in.MinAvailable
	}
	in.Resources.DeepCopyInto(&out.Resources)
	if in.Env != nil {
		out.Env = make([]corev1.EnvVar, len(in.Env))
		for i := range in.Env {
			in.Env[i].DeepCopyInto(&out.Env[i])
		}
	}
	if in.ServiceAccountAnnotations != nil {
		out.ServiceAccountAnnotations = make(map[string]string, len(in.ServiceAccountAnnotations))
		for k, v := range in.ServiceAccountAnnotations {
			out.ServiceAccountAnnotations[k] = v
		}
	}
}

func (in *AppWorkloadStatus) DeepCopyInto(out *AppWorkloadStatus) {
	*out = *in
	if in.Conditions != nil {
		out.Conditions = make([]metav1.Condition, len(in.Conditions))
		for i := range in.Conditions {
			in.Conditions[i].DeepCopyInto(&out.Conditions[i])
		}
	}
}

func (in *AppWorkload) DeepCopyInto(out *AppWorkload) {
	*out = *in
	out.TypeMeta = in.TypeMeta
	in.ObjectMeta.DeepCopyInto(&out.ObjectMeta)
	in.Spec.DeepCopyInto(&out.Spec)
	in.Status.DeepCopyInto(&out.Status)
}

func (in *AppWorkload) DeepCopy() *AppWorkload {
	if in == nil {
		return nil
	}
	out := new(AppWorkload)
	in.DeepCopyInto(out)
	return out
}

func (in *AppWorkload) DeepCopyObject() runtime.Object {
	if c := in.DeepCopy(); c != nil {
		return c
	}
	return nil
}

func (in *AppWorkloadList) DeepCopyInto(out *AppWorkloadList) {
	*out = *in
	out.TypeMeta = in.TypeMeta
	in.ListMeta.DeepCopyInto(&out.ListMeta)
	if in.Items != nil {
		out.Items = make([]AppWorkload, len(in.Items))
		for i := range in.Items {
			in.Items[i].DeepCopyInto(&out.Items[i])
		}
	}
}

func (in *AppWorkloadList) DeepCopy() *AppWorkloadList {
	if in == nil {
		return nil
	}
	out := new(AppWorkloadList)
	in.DeepCopyInto(out)
	return out
}

func (in *AppWorkloadList) DeepCopyObject() runtime.Object {
	if c := in.DeepCopy(); c != nil {
		return c
	}
	return nil
}
