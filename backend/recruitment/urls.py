from rest_framework.routers import DefaultRouter

from .views import CandidateViewSet, JobPostingViewSet

router = DefaultRouter()
router.register("jobs", JobPostingViewSet, basename="job")
router.register("candidates", CandidateViewSet, basename="candidate")

urlpatterns = router.urls
