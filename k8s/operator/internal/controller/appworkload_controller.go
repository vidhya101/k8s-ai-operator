// Package controller implements the AppWorkload reconciler: one CR in, a Deployment + Service +
// ServiceAccount (+ optional HPA/PDB) out. This is the "operator concept" half of the platform —
// the same generic objects k8s/app/base/*.yaml hand-writes are instead generated here from a
// single declarative CR, so a platform team can offer `kubectl apply -f my-app.yaml` (one
// AppWorkload) as the paved-road path instead of asking every service team to hand-maintain a
// Kustomize overlay.
package controller

import (
	"context"
	"fmt"

	appsv1 "k8s.io/api/apps/v1"
	autoscalingv2 "k8s.io/api/autoscaling/v2"
	corev1 "k8s.io/api/core/v1"
	policyv1 "k8s.io/api/policy/v1"
	apierrors "k8s.io/apimachinery/pkg/api/errors"
	apimeta "k8s.io/apimachinery/pkg/api/meta"
	"k8s.io/apimachinery/pkg/api/resource"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime"
	"k8s.io/apimachinery/pkg/types"
	"k8s.io/apimachinery/pkg/util/intstr"
	ctrl "sigs.k8s.io/controller-runtime"
	"sigs.k8s.io/controller-runtime/pkg/client"
	"sigs.k8s.io/controller-runtime/pkg/controller/controllerutil"
	"sigs.k8s.io/controller-runtime/pkg/log"

	platformv1alpha1 "github.com/vidhya101/devsecops-platform/k8s/operator/api/v1alpha1"
)

const (
	fieldOwner    = "appworkload-operator"
	labelManaged  = "app.kubernetes.io/managed-by"
	labelName     = "app.kubernetes.io/name"
	labelInstance = "app.kubernetes.io/instance"
)

// AppWorkloadReconciler reconciles an AppWorkload object.
type AppWorkloadReconciler struct {
	client.Client
	Scheme *runtime.Scheme
}

// +kubebuilder:rbac:groups=platform.io,resources=appworkloads,verbs=get;list;watch;create;update;patch;delete
// +kubebuilder:rbac:groups=platform.io,resources=appworkloads/status,verbs=get;update;patch
// +kubebuilder:rbac:groups=platform.io,resources=appworkloads/finalizers,verbs=update
// +kubebuilder:rbac:groups=apps,resources=deployments,verbs=get;list;watch;create;update;patch;delete
// +kubebuilder:rbac:groups="",resources=services;serviceaccounts,verbs=get;list;watch;create;update;patch;delete
// +kubebuilder:rbac:groups=autoscaling,resources=horizontalpodautoscalers,verbs=get;list;watch;create;update;patch;delete
// +kubebuilder:rbac:groups=policy,resources=poddisruptionbudgets,verbs=get;list;watch;create;update;patch;delete
// +kubebuilder:rbac:groups="",resources=events,verbs=create;patch

func (r *AppWorkloadReconciler) Reconcile(ctx context.Context, req ctrl.Request) (ctrl.Result, error) {
	logger := log.FromContext(ctx)

	var workload platformv1alpha1.AppWorkload
	if err := r.Get(ctx, req.NamespacedName, &workload); err != nil {
		if apierrors.IsNotFound(err) {
			return ctrl.Result{}, nil // deleted; owned objects are garbage-collected via owner refs
		}
		return ctrl.Result{}, fmt.Errorf("get AppWorkload: %w", err)
	}

	labels := map[string]string{
		labelName:     "app",
		labelInstance: workload.Name,
		labelManaged:  fieldOwner,
	}
	if workload.Spec.Cloud != "" {
		labels["platform.io/cloud"] = workload.Spec.Cloud
	}

	if err := r.reconcileServiceAccount(ctx, &workload, labels); err != nil {
		return ctrl.Result{}, fmt.Errorf("reconcile ServiceAccount: %w", err)
	}
	if err := r.reconcileDeployment(ctx, &workload, labels); err != nil {
		return ctrl.Result{}, fmt.Errorf("reconcile Deployment: %w", err)
	}
	if err := r.reconcileService(ctx, &workload, labels); err != nil {
		return ctrl.Result{}, fmt.Errorf("reconcile Service: %w", err)
	}
	if workload.Spec.MinReplicas != nil && workload.Spec.MaxReplicas != nil {
		if err := r.reconcileHPA(ctx, &workload, labels); err != nil {
			return ctrl.Result{}, fmt.Errorf("reconcile HPA: %w", err)
		}
	}
	if err := r.reconcilePDB(ctx, &workload, labels); err != nil {
		return ctrl.Result{}, fmt.Errorf("reconcile PDB: %w", err)
	}

	if err := r.updateStatus(ctx, &workload); err != nil {
		logger.Error(err, "status update failed; will retry on next reconcile")
	}

	return ctrl.Result{}, nil
}

func (r *AppWorkloadReconciler) reconcileServiceAccount(ctx context.Context, w *platformv1alpha1.AppWorkload, labels map[string]string) error {
	sa := &corev1.ServiceAccount{ObjectMeta: metav1.ObjectMeta{Name: w.Name, Namespace: w.Namespace}}
	_, err := controllerutil.CreateOrUpdate(ctx, r.Client, sa, func() error {
		sa.Labels = labels
		if sa.Annotations == nil {
			sa.Annotations = map[string]string{}
		}
		for k, v := range w.Spec.ServiceAccountAnnotations {
			sa.Annotations[k] = v
		}
		falseVal := false
		sa.AutomountServiceAccountToken = &falseVal
		return controllerutil.SetControllerReference(w, sa, r.Scheme)
	})
	return err
}

func (r *AppWorkloadReconciler) reconcileDeployment(ctx context.Context, w *platformv1alpha1.AppWorkload, labels map[string]string) error {
	port := w.Spec.Port
	if port == 0 {
		port = 8080
	}
	livenessPath := w.Spec.LivenessPath
	if livenessPath == "" {
		livenessPath = "/healthz"
	}
	readinessPath := w.Spec.ReadinessPath
	if readinessPath == "" {
		readinessPath = "/readyz"
	}
	replicas := w.Spec.Replicas
	if replicas == nil {
		two := int32(2)
		replicas = &two
	}

	runAsNonRoot := true
	runAsUser := int64(10001)
	allowPrivEsc := false
	readOnlyRootFS := true

	dep := &appsv1.Deployment{ObjectMeta: metav1.ObjectMeta{Name: w.Name, Namespace: w.Namespace}}
	_, err := controllerutil.CreateOrUpdate(ctx, r.Client, dep, func() error {
		dep.Labels = labels

		// Only set desired Replicas on create — once an HPA owns this Deployment, letting the
		// reconciler keep stomping .spec.replicas back would fight the HPA every interval.
		if dep.CreationTimestamp.IsZero() {
			dep.Spec.Replicas = replicas
		}

		dep.Spec.Selector = &metav1.LabelSelector{MatchLabels: map[string]string{labelInstance: w.Name}}
		dep.Spec.Template.ObjectMeta.Labels = map[string]string{labelInstance: w.Name, labelName: "app"}
		dep.Spec.Template.Spec = corev1.PodSpec{
			ServiceAccountName: w.Name,
			SecurityContext: &corev1.PodSecurityContext{
				RunAsNonRoot: &runAsNonRoot,
				RunAsUser:    &runAsUser,
				SeccompProfile: &corev1.SeccompProfile{
					Type: corev1.SeccompProfileTypeRuntimeDefault,
				},
			},
			Containers: []corev1.Container{{
				Name:  "app",
				Image: w.Spec.Image,
				Ports: []corev1.ContainerPort{{Name: "http", ContainerPort: port}},
				Env:   w.Spec.Env,
				SecurityContext: &corev1.SecurityContext{
					AllowPrivilegeEscalation: &allowPrivEsc,
					ReadOnlyRootFilesystem:   &readOnlyRootFS,
					Capabilities:             &corev1.Capabilities{Drop: []corev1.Capability{"ALL"}},
				},
				Resources: resourcesOrDefault(w.Spec.Resources),
				LivenessProbe: &corev1.Probe{
					ProbeHandler:     corev1.ProbeHandler{HTTPGet: &corev1.HTTPGetAction{Path: livenessPath, Port: intstr.FromString("http")}},
					PeriodSeconds:    10,
					TimeoutSeconds:   2,
					FailureThreshold: 3,
				},
				ReadinessProbe: &corev1.Probe{
					ProbeHandler:     corev1.ProbeHandler{HTTPGet: &corev1.HTTPGetAction{Path: readinessPath, Port: intstr.FromString("http")}},
					PeriodSeconds:    5,
					TimeoutSeconds:   2,
					FailureThreshold: 3,
				},
			}},
		}
		return controllerutil.SetControllerReference(w, dep, r.Scheme)
	})
	return err
}

func resourcesOrDefault(r corev1.ResourceRequirements) corev1.ResourceRequirements {
	if r.Requests == nil && r.Limits == nil {
		// Deliberately conservative fallback if the CR omits Resources entirely — the
		// namespace's LimitRange (k8s/app/base/limitrange.yaml) would apply this same shape on
		// admission anyway; setting it here just makes `kubectl get deploy -o yaml` self-explanatory
		// without requiring a second `kubectl describe limitrange` to see why.
		return corev1.ResourceRequirements{
			Requests: corev1.ResourceList{
				corev1.ResourceCPU:    resource.MustParse("100m"),
				corev1.ResourceMemory: resource.MustParse("128Mi"),
			},
			Limits: corev1.ResourceList{
				corev1.ResourceCPU:    resource.MustParse("500m"),
				corev1.ResourceMemory: resource.MustParse("512Mi"),
			},
		}
	}
	return r
}

func (r *AppWorkloadReconciler) reconcileService(ctx context.Context, w *platformv1alpha1.AppWorkload, labels map[string]string) error {
	port := w.Spec.Port
	if port == 0 {
		port = 8080
	}
	svc := &corev1.Service{ObjectMeta: metav1.ObjectMeta{Name: w.Name, Namespace: w.Namespace}}
	_, err := controllerutil.CreateOrUpdate(ctx, r.Client, svc, func() error {
		svc.Labels = labels
		svc.Spec.Selector = map[string]string{labelInstance: w.Name}
		svc.Spec.Ports = []corev1.ServicePort{{
			Name:       "http",
			Port:       80,
			TargetPort: intstr.FromString("http"),
		}}
		return controllerutil.SetControllerReference(w, svc, r.Scheme)
	})
	return err
}

func (r *AppWorkloadReconciler) reconcileHPA(ctx context.Context, w *platformv1alpha1.AppWorkload, labels map[string]string) error {
	target := int32(70)
	if w.Spec.TargetCPUUtilizationPercentage != nil {
		target = *w.Spec.TargetCPUUtilizationPercentage
	}
	hpa := &autoscalingv2.HorizontalPodAutoscaler{ObjectMeta: metav1.ObjectMeta{Name: w.Name, Namespace: w.Namespace}}
	_, err := controllerutil.CreateOrUpdate(ctx, r.Client, hpa, func() error {
		hpa.Labels = labels
		hpa.Spec.ScaleTargetRef = autoscalingv2.CrossVersionObjectReference{
			APIVersion: "apps/v1", Kind: "Deployment", Name: w.Name,
		}
		hpa.Spec.MinReplicas = w.Spec.MinReplicas
		hpa.Spec.MaxReplicas = *w.Spec.MaxReplicas
		hpa.Spec.Metrics = []autoscalingv2.MetricSpec{{
			Type: autoscalingv2.ResourceMetricSourceType,
			Resource: &autoscalingv2.ResourceMetricSource{
				Name:   corev1.ResourceCPU,
				Target: autoscalingv2.MetricTarget{Type: autoscalingv2.UtilizationMetricType, AverageUtilization: &target},
			},
		}}
		return controllerutil.SetControllerReference(w, hpa, r.Scheme)
	})
	return err
}

func (r *AppWorkloadReconciler) reconcilePDB(ctx context.Context, w *platformv1alpha1.AppWorkload, labels map[string]string) error {
	minAvailable := int32(1)
	if w.Spec.MinAvailable != nil {
		minAvailable = *w.Spec.MinAvailable
	}
	minAvailableIS := intstr.FromInt(int(minAvailable))

	pdb := &policyv1.PodDisruptionBudget{ObjectMeta: metav1.ObjectMeta{Name: w.Name, Namespace: w.Namespace}}
	_, err := controllerutil.CreateOrUpdate(ctx, r.Client, pdb, func() error {
		pdb.Labels = labels
		pdb.Spec.MinAvailable = &minAvailableIS
		pdb.Spec.Selector = &metav1.LabelSelector{MatchLabels: map[string]string{labelInstance: w.Name}}
		return controllerutil.SetControllerReference(w, pdb, r.Scheme)
	})
	return err
}

func (r *AppWorkloadReconciler) updateStatus(ctx context.Context, w *platformv1alpha1.AppWorkload) error {
	var dep appsv1.Deployment
	if err := r.Get(ctx, types.NamespacedName{Name: w.Name, Namespace: w.Namespace}, &dep); err != nil {
		return err
	}
	w.Status.ObservedGeneration = w.Generation
	w.Status.ReadyReplicas = dep.Status.ReadyReplicas
	apimeta.SetStatusCondition(&w.Status.Conditions, buildReadyCondition(dep))
	return r.Status().Update(ctx, w)
}

func buildReadyCondition(dep appsv1.Deployment) metav1.Condition {
	if dep.Status.ReadyReplicas > 0 && dep.Status.ReadyReplicas == dep.Status.Replicas {
		return metav1.Condition{Type: "Ready", Status: metav1.ConditionTrue, Reason: "DeploymentAvailable", Message: "all replicas ready"}
	}
	return metav1.Condition{Type: "Ready", Status: metav1.ConditionFalse, Reason: "DeploymentProgressing", Message: "waiting for replicas to become ready"}
}

// SetupWithManager wires the reconciler into the manager and watches every object it owns, so an
// out-of-band edit (someone runs `kubectl edit deployment`) gets reconciled back, not just
// changes to the AppWorkload CR itself.
func (r *AppWorkloadReconciler) SetupWithManager(mgr ctrl.Manager) error {
	return ctrl.NewControllerManagedBy(mgr).
		For(&platformv1alpha1.AppWorkload{}).
		Owns(&appsv1.Deployment{}).
		Owns(&corev1.Service{}).
		Owns(&corev1.ServiceAccount{}).
		Owns(&policyv1.PodDisruptionBudget{}).
		Owns(&autoscalingv2.HorizontalPodAutoscaler{}).
		Complete(r)
}
