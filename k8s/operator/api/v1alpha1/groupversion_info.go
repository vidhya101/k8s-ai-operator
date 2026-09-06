// Package v1alpha1 contains the AppWorkload CRD API — the operator's single custom resource.
// +kubebuilder:object:generate=true
// +groupName=platform.io
package v1alpha1

import (
	"k8s.io/apimachinery/pkg/runtime/schema"
	"sigs.k8s.io/controller-runtime/pkg/scheme"
)

var (
	// GroupVersion is group platform.io, version v1alpha1.
	GroupVersion = schema.GroupVersion{Group: "platform.io", Version: "v1alpha1"}

	// SchemeBuilder is used to add go types to the GroupVersionKind scheme.
	SchemeBuilder = &scheme.Builder{GroupVersion: GroupVersion}

	// AddToScheme adds the types in this group-version to the given scheme.
	AddToScheme = SchemeBuilder.AddToScheme
)

func init() {
	SchemeBuilder.Register(&AppWorkload{}, &AppWorkloadList{})
}
