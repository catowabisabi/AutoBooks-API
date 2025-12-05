from rest_framework import viewsets
from .serializers import DesignationSerializer, DepartmentSerializer, LeaveApplicationSerializer, ProjectSerializer, TaskSerializer
from .models import Designation, Department, LeaveTypes, Project, ProjectStatuses, Task, LeaveApplication, TaskStatuses
from rest_framework.decorators import action
from rest_framework.response import Response


class DesignationViewset(viewsets.ModelViewSet):
    serializer_class = DesignationSerializer
    queryset = Designation.objects.all().order_by('id')

class DepartmentViewset(viewsets.ModelViewSet):
    serializer_class = DepartmentSerializer
    queryset = Department.objects.all().order_by('id')

class ProjectViewset(viewsets.ModelViewSet):
    serializer_class = ProjectSerializer
    queryset = Project.objects.all().order_by('id')

    @action(detail=False, methods=['get'], url_path='project_statuses', url_name='project_statuses')
    def project_statuses(self, request):
        """
        Returns a list of available project statuses.
        """
        project_statuses = [status.value for status in ProjectStatuses]
        return Response({'project_statuses': project_statuses}, status=200)

class TaskViewset(viewsets.ModelViewSet):
    serializer_class = TaskSerializer
    queryset = Task.objects.all().order_by('id')

    @action(detail=False, methods=['get'], url_path='task_statuses', url_name='task_statuses')
    def task_statuses(self, request):
        """
        Returns a list of available task statuses.
        """
        task_statuses = [status.value for status in TaskStatuses]
        return Response({'task_statuses': task_statuses}, status=200)

class LeaveApplicationViewset(viewsets.ModelViewSet):
    serializer_class = LeaveApplicationSerializer
    queryset = LeaveApplication.objects.all().order_by('id')

    @action(detail=False, methods=['get'], url_path='leave_types', url_name='leave_types')
    def leave_types(self, request):
        """
        Returns a list of available leave types.
        """
        leave_types = [leave_type.value for leave_type in LeaveTypes]
        return Response({'leave_types': leave_types}, status=200)
