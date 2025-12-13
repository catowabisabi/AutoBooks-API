import uuid
from django.db import models
from core.models import BaseModel
from core.tenants.models import Tenant
from hrms.models import Employee
from users.models import User


class Project(BaseModel):
    tenant = models.ForeignKey(Tenant, on_delete=models.PROTECT, related_name='projects')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    members = models.ManyToManyField(Employee, related_name='projects')

    def __str__(self):
        return self.name


class TaskBoard(BaseModel):
    project = models.ForeignKey(Project, on_delete=models.PROTECT, related_name='boards')
    name = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.name} - {self.project.name}"


class Task(BaseModel):
    board = models.ForeignKey(TaskBoard, on_delete=models.PROTECT, related_name='tasks')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    assignees = models.ManyToManyField(Employee, related_name='tasks')
    due_date = models.DateField(null=True, blank=True)
    is_completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class TaskComment(BaseModel):
    task = models.ForeignKey(Task, on_delete=models.PROTECT, related_name='comments')
    user = models.ForeignKey(User, on_delete=models.PROTECT)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Comment by {self.user.full_name} on {self.task.title}"
